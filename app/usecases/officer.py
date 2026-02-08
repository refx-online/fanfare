from __future__ import annotations

import app.settings
from app.discord import Webhook
from app.constants.privileges import Privileges
from app.repositories import client_hashes as client_hash_repo


async def inform(name: str, user_id: int, t: str, r: str, gate: str) -> None:
    """
    Uh oh! sketchy..
    """
    if webhook_url := app.settings.DISCORD_AUDIT_LOG_WEBHOOK:
        await Webhook(
            webhook_url,
            content=f"<{name} ({user_id})> {t} on {gate} gate, {r}",
        ).post()

async def validate_user_certificate(
    user_info: dict,
    login_data: dict,
    running_under_wine: bool,
    inactionable_disk_hashes: list[str] | None = None,
) -> bool:
    """
    handle hardware id checking and potential multi-account detection.
    NOTE: experimental feature, no ban/restrict-ing account for now.
    """
    inactionable_disk_hashes = inactionable_disk_hashes or []
    
    disk_serial_for_check = (
        None
        if login_data["disk_signature_md5"] in inactionable_disk_hashes
        else login_data["disk_signature_md5"]
    )

    hw_matches = await client_hash_repo.fetch_any_hardware_matches_for_user(
        userid=user_info["id"],
        running_under_wine=running_under_wine,
        adapters=login_data["adapters_md5"],
        uninstall_id=login_data["uninstall_md5"],
        disk_serial=disk_serial_for_check,
    )

    # I have like 2 test accounts
    # TODO: should i make a toggle for the user like "allow hw validation bypass"?
    #       for certain player that couldn't log into their account
    if user_info["priv"] & Privileges.DEVELOPER or any(
        m["priv"] & Privileges.DEVELOPER for m in hw_matches
    ):
        return True

    user_matches: dict[int, set[str]] = {}
    for hw in hw_matches:
        userid = hw["userid"]
        if userid not in user_matches:
            user_matches[userid] = set()

        if hw["adapters"] == login_data["adapters_md5"]:
            user_matches[userid].add("adapters")
        if hw["uninstall_id"] == login_data["uninstall_md5"]:
            user_matches[userid].add("uninstall_id")
        if (
            login_data["disk_signature_md5"]
            and login_data["disk_signature_md5"] not in inactionable_disk_hashes
            and hw["disk_serial"] == login_data["disk_signature_md5"]
        ):
            user_matches[userid].add("disk_serial")

    max_match_strength = max((len(m) for m in user_matches.values()), default=0)

    all_matched_fields = set()
    for fields in user_matches.values():
        all_matched_fields.update(fields)

    # wine users. only the unique_id is somewhat reliable.
    threshold = 3 if running_under_wine else 2

    exact_matches = [
        hw
        for hw in hw_matches
        if (
            hw["adapters"] == login_data["adapters_md5"]
            and hw["uninstall_id"] == login_data["uninstall_md5"]
            and hw["disk_serial"] == login_data["disk_signature_md5"]
            and login_data["adapters_md5"]
            and login_data["uninstall_md5"]
            and login_data["disk_signature_md5"]
        )
    ]

    if exact_matches:
        exact_match_users = {hw["userid"]: hw for hw in exact_matches}
        sorted_user_ids = sorted(exact_match_users.keys())
        main_user_id = sorted_user_ids[0]
        alt_user_ids = sorted_user_ids[1:]

        if user_info["id"] != main_user_id:
            alt_user_ids.append(user_info["id"])

        main_user = exact_match_users[main_user_id]

        # TODO: "restrict" their main account.
        for alt_id in alt_user_ids:
            if alt_id == user_info["id"]:
                # don't save hardware, we're blocking this login
                await inform(
                    name=user_info["name"],
                    user_id=user_info["id"],
                    t="hardware flagged",
                    r=f"exact hwid match with <{main_user['name']} ({main_user_id})>",
                    gate="login",
                )
                return False
            else:
                # TODO: "ban" the alt accounts
                ...

    if hw_matches and max_match_strength >= threshold:
        if not (user_info["priv"] & Privileges.VERIFIED):
            unique_user_count = len(user_matches)
            reason = f"{unique_user_count} users ({', '.join(sorted(all_matched_fields)) or 'none'}), strength={max_match_strength}/{threshold}"
            
            await inform(
                name=user_info["name"],
                user_id=user_info["id"],
                t="possible multi account",
                r=reason,
                gate="login"
            )

    await client_hash_repo.create(
        userid=user_info["id"],
        osupath=login_data["osu_path_md5"],
        adapters=login_data["adapters_md5"],
        uninstall_id=login_data["uninstall_md5"],
        disk_serial=login_data["disk_signature_md5"],
    )

    return True