"""cho: handles login and validates it."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from datetime import date
from datetime import datetime
from typing import Literal
from typing import TypedDict

import bcrypt
from fastapi import APIRouter
from fastapi import Response
from fastapi.param_functions import Header
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

import app.packets
import app.settings
import app.state
import app.usecases.officer
from app._typing import IPAddress
from app.constants import regexes
from app.constants.privileges import ClanPrivileges
from app.constants.privileges import ClientPrivileges
from app.constants.privileges import Privileges
from app.discord import Webhook
from app.logging import Ansi
from app.logging import log
from app.objects.player import ClientDetails
from app.objects.player import OsuStream
from app.objects.player import OsuVersion
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import LoginFailureReason
from app.repositories import ingame_logins as logins_repo
from app.repositories import mail as mail_repo
from app.repositories import users as users_repo

OSU_API_V2_CHANGELOG_URL = "https://osu.ppy.sh/api/v2/changelog"

BASE_DOMAIN = app.settings.DOMAIN

router = APIRouter(tags=["Bancho API"])

CHO_GET_RESP = """
<!DOCTYPE html>
<style>
body {{
    background: black;
    color: gray;
    font-family: monospace;
    overflow-x: hidden;
}}
#art {{
    position: relative;
    white-space: pre;
    animation: sailLeft 5s linear infinite;
}}

@keyframes sailLeft {{
    0% {{
        left: -100vw;
    }}
    100% {{
        left: 100%;
    }}
}}
</style>
<body>
<pre>
          _____                    _____                    _____
         /\\    \\                  /\\    \\                  /\\    \\                 ______
        /::\\    \\                /::\\    \\                /::\\    \\               |::|   |
       /::::\\    \\              /::::\\    \\              /::::\\    \\              |::|   |
      /::::::\\    \\            /::::::\\    \\            /::::::\\    \\             |::|   |
     /:::/\\:::\\    \\          /:::/\\:::\\    \\          /:::/\\:::\\    \\            |::|   |
    /:::/__\\:::\\    \\        /:::/__\\:::\\    \\        /:::/__\\:::\\    \\           |::|   |
   /::::\\   \\:::\\    \\      /::::\\   \\:::\\    \\      /::::\\   \\:::\\    \\          |::|   |
  /::::::\\   \\:::\\    \\    /::::::\\   \\:::\\    \\    /::::::\\   \\:::\\    \\         |::|   |
 /:::/\\:::\\   \\:::\\____\\  /:::/\\:::\\   \\:::\\    \\  /:::/\\:::\\   \\:::\\    \\  ______|::|___|___ ____
/:::/  \\:::\\   \\:::|    |/:::/__\\:::\\   \\:::\\____\\/:::/  \\:::\\   \\:::\\____\\|:::::::::::::::::|    |
\\::/   |::::\\  /:::|____|\\:::\\   \\:::\\   \\::/    /\\::/    \\:::\\   \\::/    /|:::::::::::::::::|____|
 \\/____|:::::\\/:::/    /  \\:::\\   \\:::\\   \\/____/  \\/____/ \\:::\\   \\/____/  ~~~~~~|::|~~~|~~~
       |:::::::::/    /    \\:::\\   \\:::\\    \\               \\:::\\    \\            |::|   |
       |::|\\::::/    /      \\:::\\   \\:::\\____\\               \\:::\\____\\           |::|   |
       |::| \\::/____/        \\:::\\   \\::/    /                \\::/    /           |::|   |
       |::|  ~|               \\:::\\   \\/____/                  \\/____/            |::|   |
       |::|   |                \\:::\\    \\                                         |::|   |
       \\::|   |                 \\:::\\____\\                                        |::|   |
        \\:|   |                  \\::/    /                                        |::|___|
         \\|___|                   \\/____/                                          ~~
</pre>
running on gulag/bancho.py (edited) and prayers<br>
<pre id="art">
                 .  o ..
                 o . o o.o
                      ...oo
                        __[]__          vroom vroooooommmm
                     __|_o_o_o\\__
                     \\\"\"\"\"\"\"\"\"\"\"/
                      \\. ..  . /
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
</pre>
see whos online: <a href="/online">https://c.{domain}/online</a><br>
ongoing matches: <a href="/matches">https://c.{domain}/matches</a><br>
web: <a href="https://{domain}">https://{domain}</a><br>
</body>
</html>"""


@router.get("/")
async def bancho_http_handler() -> Response:
    """Handle a request from a web browser."""
    return HTMLResponse(
        CHO_GET_RESP.format(
            domain=BASE_DOMAIN,
        ),
    )


@router.get("/online")
async def bancho_view_online_users() -> Response:
    """see who's online"""
    new_line = "\n"

    players: list[Player] = []
    bots: list[Player] = []
    for p in app.state.sessions.players:
        if p.is_bot_client:
            bots.append(p)
        else:
            players.append(p)

    id_max_length = len(str(max(p.id for p in app.state.sessions.players)))

    return HTMLResponse(
        f"""
<!DOCTYPE html>
<body style="font-family: monospace;  white-space: pre-wrap;"><a href="/">back</a>
users:
{new_line.join([f"({p.id:>{id_max_length}}): {p.safe_name}" for p in players])}
bots:
{new_line.join(f"({p.id:>{id_max_length}}): {p.safe_name}" for p in bots)}
</body>
</html>""",
    )


@router.get("/matches")
async def bancho_view_matches() -> Response:
    """ongoing matches"""
    new_line = "\n"

    ON_GOING = "ongoing"
    IDLE = "idle"
    max_status_length = len(max(ON_GOING, IDLE))

    BEATMAP = "beatmap"
    HOST = "host"
    max_properties_length = max(len(BEATMAP), len(HOST))

    matches = [m for m in app.state.sessions.matches if m is not None]

    match_id_max_length = (
        len(str(max(match.id for match in matches))) if len(matches) else 0
    )

    return HTMLResponse(
        f"""
<!DOCTYPE html>
<body style="font-family: monospace;  white-space: pre-wrap;"><a href="/">back</a>
matches:
{
            new_line.join(
                f'''{(ON_GOING if m.in_progress else IDLE):<{max_status_length}} ({m.id:>{match_id_max_length}}): {m.name}
-- '''
                + f"{new_line}-- ".join([
                    f'{BEATMAP:<{max_properties_length}}: {m.map_name}',
                    f'{HOST:<{max_properties_length}}: <{m.host.id}> {m.host.safe_name}',
                ]) for m in matches
            )
        }
</body>
</html>""",
    )


@router.get("/infos")
async def bancho_view_infos() -> Response:
    """Get server information"""
    data = {
        "version": 1,
        "latestClientVersion": "20240206.2",
        "motd": "Welcome aboard. aeris player!",
        "onlineUsers": len(
            [
                player
                for player in app.state.sessions.players
                if not player.is_bot_client
            ],
        ),
        "icon": f"https://{BASE_DOMAIN}/static/favicon.png",
    }

    return JSONResponse(data)


@router.post("/")
async def bancho_handler(
    request: Request,
    osu_token: str | None = Header(None),
    user_agent: Literal["osu!"] = Header(...),
) -> Response:
    ip = app.state.services.ip_resolver.get_ip(request.headers)

    if osu_token is None:
        # the client is performing a login
        login_data = await handle_osu_login_request(
            request.headers,
            await request.body(),
            ip,
        )

        return Response(
            content=login_data["response_body"],
            headers={"cho-token": login_data["osu_token"]},
        )

    # get the player from the specified osu token.
    player = app.state.sessions.players.get(token=osu_token)

    if not player:
        # chances are, we just restarted the server
        # tell their client to reconnect immediately.
        return Response(
            content=(
                app.packets.notification(
                    "You don't seem to be logged into refx anymore... "
                    "This is common during server restarts, trying to log you back in.",
                )
                + app.packets.restart_server(0)  # ms until reconnection
            ),
        )

    if player.restricted:
        # restricted users may only use certain packet handlers.
        packet_map = app.state.packets["restricted"]
    else:
        packet_map = app.state.packets["all"]

    # bancho connections can be comprised of multiple packets;
    # our reader is designed to iterate through them individually,
    # allowing logic to be implemented around the actual handler.
    # NOTE: any unhandled packets will be ignored internally.

    with memoryview(await request.body()) as body_view:
        for packet in BanchoPacketReader(body_view, packet_map):
            await packet.handle(player)

    player.last_recv_time = time.time()

    response_data = player.dequeue()
    return Response(content=response_data)


# Some messages to send on welcome/restricted/etc.
# TODO: these should probably be moved to the config.
RESTRICTED_MSG = (
    "yo twin, we detected some suspicious activity on one of your scores, and as a result, "
    "yo bumass has been temporarily restricted. "
    "ts could be due to things like unusual pp gains, replay issues, or data mismatches. "
    "to resolve ts, yo need to submit a liveplay. "
    "a full screen recording of you playing a similar map with handcam + game audio (or without audio). "
    "make sure everything is visible: yo screen, yo tablet, and shi. "
    "once yo submit the liveplay, we will review it and lift the restriction if everything checks out. "
)

WELCOME_NOTIFICATION = app.packets.notification(
    "Welcome aboard.",
)

OFFLINE_NOTIFICATION = app.packets.notification(
    "The server is currently running in offline mode; "
    "some features will be unavailable.",
)

FORLORN_NOTIFICATION = app.packets.notification(
    "forlorn (Score Service) is down\n"
    "Please wait until further notice. "
    "leaderboard & score submission might not work.",
)


class LoginResponse(TypedDict):
    osu_token: str
    response_body: bytes


class LoginData(TypedDict):
    username: str
    password_md5: bytes
    osu_version: str
    utc_offset: int
    display_city: bool
    pm_private: bool
    osu_path_md5: str
    adapters_str: str
    adapters_md5: str
    uninstall_md5: str
    disk_signature_md5: str


def parse_login_data(data: bytes) -> LoginData:
    """Parse data from the body of a login request."""
    (
        username,
        password_md5,
        remainder,
    ) = data.decode().split("\n", maxsplit=2)

    (
        osu_version,
        utc_offset,
        display_city,
        client_hashes,
        pm_private,
    ) = remainder.split("|", maxsplit=4)

    (
        osu_path_md5,
        adapters_str,
        adapters_md5,
        uninstall_md5,
        disk_signature_md5,
    ) = client_hashes[:-1].split(":", maxsplit=4)

    return {
        "username": username,
        "password_md5": password_md5.encode(),
        "osu_version": osu_version,
        "utc_offset": int(utc_offset),
        "display_city": display_city == "1",
        "pm_private": pm_private == "1",
        "osu_path_md5": osu_path_md5,
        "adapters_str": adapters_str,
        "adapters_md5": adapters_md5,
        "uninstall_md5": uninstall_md5,
        "disk_signature_md5": disk_signature_md5,
    }


def parse_osu_version_string(osu_version_string: str) -> OsuVersion | None:
    match = regexes.OSU_VERSION.match(osu_version_string)
    if match is None:
        return None

    osu_version = OsuVersion(
        date=date(
            year=int(match["date"][0:4]),
            month=int(match["date"][4:6]),
            day=int(match["date"][6:8]),
        ),
        revision=int(match["revision"]) if match["revision"] else None,
        stream=OsuStream(match["stream"] or "stable"),
        refx=match["ver"] == "Re;fx b",
        refx_dev=match["stream"] == "dev",  # this shit is stupid
    )
    return osu_version


async def get_allowed_client_versions(osu_stream: OsuStream) -> set[date] | None:
    """
    Return a list of acceptable client versions for the given stream.

    This is used to determine whether a client is too old to connect to the server.

    Returns None if the connection to the osu! api fails.
    """
    osu_stream_strs = []
    allowed_client_versions: set[date] = set()

    if osu_stream == OsuStream.STABLE:
        osu_stream_strs.append(osu_stream.value + "40")  # i wonder why this exists
    elif osu_stream == OsuStream.TOURNEY:
        # osu!tourney clients are allowed to connect with any version
        osu_stream_strs.append("stable40")
        osu_stream_strs.append("cuttingedge")

    for osu_stream_str in osu_stream_strs:
        response = await app.state.services.http_client.get(
            OSU_API_V2_CHANGELOG_URL,
            params={"stream": osu_stream_str},
        )
        if not response.is_success:
            return None

        for build in response.json()["builds"]:
            version = date(
                int(build["version"][0:4]),
                int(build["version"][4:6]),
                int(build["version"][6:8]),
            )
            allowed_client_versions.add(version)
            if any(entry["major"] for entry in build["changelog_entries"]):
                # this build is a major iteration to the client
                # don't allow anything older than this
                break

    return allowed_client_versions


def parse_adapters_string(adapters_string: str) -> tuple[list[str], bool]:
    running_under_wine = adapters_string == "runningunderwine"
    adapters = adapters_string[:-1].split(".")
    return adapters, running_under_wine


async def authenticate(
    username: str,
    untrusted_password: bytes,
) -> users_repo.User | None:
    user_info = await users_repo.fetch_one(
        name=username,
        fetch_all_fields=True,
    )
    if user_info is None:
        return None

    trusted_hashword = user_info["pw_bcrypt"].encode()

    # in-memory bcrypt lookup cache for performance
    if trusted_hashword in app.state.cache.bcrypt:  # ~0.01 ms
        if untrusted_password != app.state.cache.bcrypt[trusted_hashword]:
            return None
    else:  # ~200ms
        if not bcrypt.checkpw(untrusted_password, trusted_hashword):
            return None

        app.state.cache.bcrypt[trusted_hashword] = untrusted_password

    return user_info


REFX_LATEST_CLIENT_HASH = "230cd99998f1a18dbc787612179bae0e"


async def check_old_client(
    headers: Mapping[str, str],
    login_data: LoginData,
    osu_version: OsuVersion,
) -> dict | None:
    if osu_version.refx_dev:
        return None

    # loki please add an identifier for your clients

    if str(osu_version) == "b20240721.1":
        # this is a stable version of aeris client
        return None

    if str(osu_version) == "b20250210.4":
        # this is a beta version of aeris client
        return None

    if login_data["osu_path_md5"] not in REFX_LATEST_CLIENT_HASH and osu_version.refx:
        # NOTE: this is spoofable
        return {
            "osu_token": "client-too-old",
            "response_body": (
                app.packets.notification("please run updater.")
                + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
            ),
        }

    if str(osu_version) == "b20200304.1":
        # og skooter?
        return {
            "osu_token": "client-too-old",
            "response_body": (
                app.packets.version_update()
                + app.packets.notification("What the hell are you trying to do?")
                + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
            ),
        }

    if str(osu_version) == "b20240729.2":
        # skooter+
        return {
            "osu_token": "client-too-old",
            "response_body": (
                app.packets.version_update()
                + app.packets.notification("Where did you even get that client.")
                + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
            ),
        }

    if str(osu_version) == "b20221029.2":
        # version frequently used by maple crack mpgh user.
        return {
            "osu_token": "client-too-old",
            "response_body": (
                app.packets.version_update()
                + app.packets.notification("Remove that malicious crack.")
                + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
            ),
        }

    if str(osu_version) == "b20240102.2":
        # osu!fx
        return {
            "osu_token": "client-too-old",
            "response_body": (
                app.packets.version_update()
                + app.packets.notification("Wow. can we forget osu!fx?")
                + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
            ),
        }

    if app.settings.DISALLOW_OLD_CLIENTS and not osu_version.refx:
        allowed_client_versions = await get_allowed_client_versions(osu_version.stream)
        # in the case where the osu! api fails, we'll allow the client to connect
        if (
            allowed_client_versions is not None
            and osu_version.date not in allowed_client_versions
        ):
            return {
                "osu_token": "client-too-old",
                "response_body": (
                    app.packets.version_update()
                    + app.packets.login_reply(LoginFailureReason.OLD_CLIENT)
                ),
            }

    return None


async def validate_forlorn_health() -> bool:
    # TODO: dont hardcode?
    health = await app.state.services.http_client.get(
        "https://osu.refx.online/api/v1/health",
    )
    if health.is_success:
        return True

    return False


async def handle_osu_login_request(
    headers: Mapping[str, str],
    body: bytes,
    ip: IPAddress,
) -> LoginResponse:
    """\
    Login has no specific packet, but happens when the osu!
    client sends a request without an 'osu-token' header.

    Request format:
      username\npasswd_md5\nosu_version|utc_offset|display_city|client_hashes|pm_private\n

    Response format:
      Packet 5 (userid), with ID:
      -1: authentication failed
      -2: old client
      -3: banned
      -4: banned
      -5: error occurred
      -6: needs supporter
      -7: password reset
      -8: requires verification
      other: valid id, logged in
    """

    # parse login data
    login_data = parse_login_data(body)

    # perform some validation & further parsing on the data

    osu_version = parse_osu_version_string(login_data["osu_version"])
    if osu_version is None:
        return {
            "osu_token": "invalid-request",
            "response_body": (
                app.packets.login_reply(LoginFailureReason.AUTHENTICATION_FAILED)
                + app.packets.notification("Please restart your osu! and try again.")
            ),
        }

    if res := await check_old_client(
        headers=headers,
        login_data=login_data,
        osu_version=osu_version,
    ):
        return res

    adapters, running_under_wine = parse_adapters_string(login_data["adapters_str"])
    if not (running_under_wine or any(adapters)):
        return {
            "osu_token": "empty-adapters",
            "response_body": (
                app.packets.login_reply(LoginFailureReason.AUTHENTICATION_FAILED)
                + app.packets.notification(
                    "You have no adapter..  what are you trying to do?",
                )
            ),
        }

    ## parsing successful

    login_time = time.time()

    # disallow multiple sessions from a single user
    # with the exception of tourney spectator clients
    player = app.state.sessions.players.get(name=login_data["username"])
    if player and osu_version.stream != "tourney":
        # check if the existing session is still active
        if (login_time - player.last_recv_time) < 10:
            return {
                "osu_token": "user-already-logged-in",
                "response_body": (
                    app.packets.login_reply(LoginFailureReason.AUTHENTICATION_FAILED)
                    + app.packets.notification("User already logged in.")
                ),
            }
        else:
            # session is not active; replace it
            player.logout()
            del player

    user_info = await authenticate(login_data["username"], login_data["password_md5"])
    if user_info is None:
        return {
            "osu_token": "incorrect-credentials",
            "response_body": (
                app.packets.notification(f"Incorrect credentials")
                + app.packets.login_reply(LoginFailureReason.AUTHENTICATION_FAILED)
            ),
        }

    if osu_version.stream is OsuStream.TOURNEY and not (
        user_info["priv"] & Privileges.DONATOR
        and user_info["priv"] & Privileges.UNRESTRICTED
    ):
        # trying to use tourney client with insufficient privileges.
        return {
            "osu_token": "no",
            "response_body": app.packets.login_reply(
                LoginFailureReason.AUTHENTICATION_FAILED,
            ),
        }

    """ login credentials verified """

    await logins_repo.create(
        user_id=user_info["id"],
        ip=str(ip),
        osu_ver=osu_version.date,
        osu_stream=osu_version.stream,
    )

    # Some disk manufacturers set constant/shared ids for their products.
    # In these cases, there's not a whole lot we can do -- we'll allow them thru.
    INACTIONABLE_DISK_SIGNATURE_MD5S: list[str] = [
        hashlib.md5(b"0").hexdigest(),  # "0" is likely the most common variant
    ]

    allow_login = await app.usecases.officer.validate_user_certificate(
        user_info=user_info,
        login_data=login_data,
        running_under_wine=running_under_wine,
        inactionable_disk_hashes=INACTIONABLE_DISK_SIGNATURE_MD5S,
    )

    if not allow_login:
        # NOTE: this is EXACT hardware match detected
        return {
            "osu_token": "contact-staff",
            "response_body": (
                app.packets.notification(
                    "Whoops, your hardware id has a log on this server!\n"
                    "If this is your first time here, please contact a staff on our discord server!",
                )
                + app.packets.login_reply(
                    LoginFailureReason.AUTHENTICATION_FAILED,
                )
            ),
        }

    dev_acc = [4, 1, 16]
    if user_info["id"] not in dev_acc:
        if app.settings.MAINTENANCE:
            return {
                "osu_token": "no",
                "response_body": app.packets.notification(
                    "Server is undergoing maintenance! Come back later..",
                ),
            }

    """ All checks passed, player is safe to login """

    # get clan & clan priv if we're in a clan
    clan_id: int | None = None
    clan_priv: ClanPrivileges | None = None
    if user_info["clan_id"] != 0:
        clan_id = user_info["clan_id"]
        clan_priv = ClanPrivileges(user_info["clan_priv"])

    db_country = user_info["country"]

    geoloc = await app.state.services.fetch_geoloc(ip, headers)

    if geoloc is None:
        return {
            "osu_token": "login-failed",
            "response_body": (
                app.packets.notification(
                    f"{BASE_DOMAIN}: Login failed. Please contact an admin.",
                )
                + app.packets.login_reply(LoginFailureReason.AUTHENTICATION_FAILED)
            ),
        }

    if db_country == "xx":
        # bugfix for old bancho.py versions when
        # country wasn't stored on registration.
        log(f"Fixing {login_data['username']}'s country.", Ansi.LGREEN)

        await users_repo.partial_update(
            id=user_info["id"],
            country=geoloc["country"]["acronym"],
        )

    client_details = ClientDetails(
        osu_version=osu_version,
        osu_path_md5=login_data["osu_path_md5"],
        adapters_md5=login_data["adapters_md5"],
        uninstall_md5=login_data["uninstall_md5"],
        disk_signature_md5=login_data["disk_signature_md5"],
        adapters=adapters,
        ip=ip,
        wine=running_under_wine,
    )

    player = Player(
        id=user_info["id"],
        name=user_info["name"],
        priv=Privileges(user_info["priv"]),
        pw_bcrypt=user_info["pw_bcrypt"].encode(),
        token=Player.generate_token(),
        clan_id=clan_id,
        clan_priv=clan_priv,
        geoloc=geoloc,
        utc_offset=login_data["utc_offset"],
        pm_private=login_data["pm_private"],
        silence_end=user_info["silence_end"],
        donor_end=user_info["donor_end"],
        client_details=client_details,
        login_time=login_time,
        is_tourney_client=osu_version.stream == "tourney",
        api_key=user_info["api_key"],
        preferred_metric=user_info["preferred_metric"],
    )

    data = bytearray(app.packets.protocol_version(19))
    data += app.packets.login_reply(player.id)

    # *real* client privileges are sent with this packet,
    # then the user's apparent privileges are sent in the
    # userPresence packets to other players. we'll send
    # supporter along with the user's privileges here,
    # but not in userPresence (so that only donators
    # show up with the yellow name in-game, but everyone
    # gets osu!direct & other in-game perks).
    data += app.packets.bancho_privileges(
        player.bancho_priv | ClientPrivileges.SUPPORTER,
    )

    data += WELCOME_NOTIFICATION

    if not await validate_forlorn_health():
        data += FORLORN_NOTIFICATION

    if not player.priv & Privileges.VERIFIED:
        await player.add_privs(Privileges.VERIFIED)

    # send all appropriate channel info to our player.
    # the osu! client will attempt to join the channels.
    for channel in app.state.sessions.channels:
        if (
            not channel.auto_join
            or not channel.can_read(player.priv)
            or channel._name == "#lobby"  # (can't be in mp lobby @ login)
        ):
            continue

        # send chan info to all players who can see
        # the channel (to update their playercounts)
        chan_info_packet = app.packets.channel_info(
            channel._name,
            channel.topic,
            len(channel.players),
        )

        data += chan_info_packet

        for o in app.state.sessions.players:
            if channel.can_read(o.priv):
                o.enqueue(chan_info_packet)

    # tells osu! to reorder channels based on config.
    data += app.packets.channel_info_end()

    # fetch some of the player's
    # information from sql to be cached.
    await player.stats_from_sql_full()
    await player.relationships_from_sql()

    # TODO: fetch player.recent_scores from sql

    # deprecated for latest client
    # being left out for 2025> client version
    data += app.packets.main_menu_icon(
        icon_url=app.settings.MENU_ICON_URL,
        onclick_url=app.settings.MENU_ONCLICK_URL,
    )
    data += app.packets.friends_list(player.friends)
    data += app.packets.silence_end(player.remaining_silence)

    # update our new player's stats, and broadcast them.
    user_data = app.packets.user_presence(player) + app.packets.user_stats(player)

    data += user_data

    if not player.restricted:
        # player is unrestricted, two way data
        for o in app.state.sessions.players:
            # enqueue us to them
            o.enqueue(user_data)

            # enqueue them to us.
            if not o.restricted:
                if o is app.state.sessions.bot:
                    # optimization for bot since it's
                    # the most frequently requested user
                    data += app.packets.bot_presence(o)
                    data += app.packets.bot_stats(o)
                else:
                    data += app.packets.user_presence(o)
                    data += app.packets.user_stats(o)

        # the player may have been sent mail while offline,
        # enqueue any messages from their respective authors.
        mail_rows = await mail_repo.fetch_all_mail_to_user(
            user_id=player.id,
            read=False,
        )

        if mail_rows:
            sent_to: set[int] = set()

            for msg in mail_rows:
                # Add "Unread messages" header as the first message
                # for any given sender, to make it clear that the
                # messages are coming from the mail system.
                if msg["from_id"] not in sent_to:
                    data += app.packets.send_message(
                        sender=msg["from_name"],
                        msg="Unread messages",
                        recipient=msg["to_name"],
                        sender_id=msg["from_id"],
                    )
                    sent_to.add(msg["from_id"])

                msg_time = datetime.fromtimestamp(msg["time"])
                data += app.packets.send_message(
                    sender=msg["from_name"],
                    msg=f'[{msg_time:%a %b %d @ %H:%M%p}] {msg["msg"]}',
                    recipient=msg["to_name"],
                    sender_id=msg["from_id"],
                )

    else:
        # player is restricted, one way data
        for o in app.state.sessions.players.unrestricted:
            # enqueue them to us.
            if o is app.state.sessions.bot:
                # optimization for bot since it's
                # the most frequently requested user
                data += app.packets.bot_presence(o)
                data += app.packets.bot_stats(o)
            else:
                data += app.packets.user_presence(o)
                data += app.packets.user_stats(o)

        data += app.packets.account_restricted()
        data += app.packets.send_message(
            sender=app.state.sessions.bot.name,
            msg=RESTRICTED_MSG,
            recipient=player.name,
            sender_id=app.state.sessions.bot.id,
        )

    # add `p` to the global player list,
    # making them officially logged in.
    app.state.sessions.players.append(player)

    if app.state.services.datadog:
        if not player.restricted:
            app.state.services.datadog.increment("bancho.online_players")  # type: ignore[no-untyped-call]

        time_taken = time.time() - login_time
        app.state.services.datadog.histogram("bancho.login_time", time_taken)  # type: ignore[no-untyped-call]

    user_os = "unix (wine)" if running_under_wine else "win32"
    country_code = player.geoloc["country"]["acronym"].upper()

    log(
        f"{player} logged in from {country_code} using {login_data['osu_version']} on {user_os}",
        Ansi.LCYAN,
    )

    player.update_latest_activity_soon()

    return {"osu_token": player.token, "response_body": bytes(data)}
