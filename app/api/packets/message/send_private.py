from __future__ import annotations

import asyncio
import re
import time
from zoneinfo import ZoneInfo

import app
import app.settings
import app.state
import app.usecases.performance
from app import commands
from app.api.packets.constants import DISK_CHAT_LOG_FILE
from app.api.packets.constants import NOW_PLAYING_RGX
from app.constants.mods import Mods
from app.logging import Ansi
from app.logging import get_timestamp
from app.logging import log
from app.logging import magnitude_fmt_time
from app.objects.beatmap import Beatmap
from app.objects.beatmap import ensure_osu_file_is_available
from app.objects.player import Action
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.repositories import mail as mail_repo
from app.usecases.performance import ScoreParams
from app.utils import fetch_bot_response


class SendPrivateMessage(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.msg = reader.read_message()

    async def handle(self, player: Player) -> None:
        if player.silenced:
            if app.settings.DEBUG:
                log(f"{player} tried to send a dm while silenced.", Ansi.LYELLOW)
            return

        # remove leading/trailing whitespace
        msg = self.msg.text.strip()

        if not msg:
            return

        target_name = self.msg.recipient

        # allow this to get from sql - players can receive
        # messages offline, due to the mail system. B)
        target = await app.state.sessions.players.from_cache_or_sql(name=target_name)
        if not target:
            if app.settings.DEBUG:
                log(
                    f"{player} tried to write to non-existent user {target_name}.",
                    Ansi.LYELLOW,
                )
            return

        if player.id in target.blocks:
            player.enqueue(app.packets.user_dm_blocked(target_name))

            if app.settings.DEBUG:
                log(f"{player} tried to message {target}, but they have them blocked.")
            return

        if target.pm_private and player.id not in target.friends:
            player.enqueue(app.packets.user_dm_blocked(target_name))

            if app.settings.DEBUG:
                log(f"{player} tried to message {target}, but they are blocking dms.")
            return

        if target.silenced:
            # if target is silenced, inform player.
            player.enqueue(app.packets.target_silenced(target_name))

            if app.settings.DEBUG:
                log(f"{player} tried to message {target}, but they are silenced.")
            return

        # limit message length to 2k chars
        # perhaps this could be dangerous with !py..?
        if len(msg) > 2000:
            msg = f"{msg[:2000]}... (truncated)"
            player.enqueue(
                app.packets.notification(
                    "Your message was truncated\n(exceeded 2000 characters).",
                ),
            )

        if target.status.action == Action.Afk and target.away_msg:
            # send away message if target is afk and has one set.
            player.send(target.away_msg, sender=target)

        if target is not app.state.sessions.bot:
            # target is not bot, send the message normally if online
            if target.is_online:
                target.send(msg, sender=player)
            else:
                # inform user they're offline, but
                # will receive the mail @ next login.
                player.enqueue(
                    app.packets.notification(
                        f"{target.name} is currently offline, but will "
                        "receive your messsage on their next login.",
                    ),
                )

            # insert mail into db, marked as unread.
            await mail_repo.create(
                from_id=player.id,
                to_id=target.id,
                msg=msg,
            )
        else:
            # messaging the bot, check for commands & /np.
            if msg.startswith(app.settings.COMMAND_PREFIX):
                cmd = await commands.process_commands(player, target, msg)
            else:
                cmd = None

            if cmd:
                # command triggered, send response if any.
                if cmd["resp"] is not None:
                    player.send(cmd["resp"], sender=target)
            else:
                # no commands triggered.
                r_match = NOW_PLAYING_RGX.match(msg)
                if r_match:
                    # user is /np'ing a map.
                    # save it to their player instance
                    # so we can use this elsewhere owo..
                    bmap = await Beatmap.from_bid(int(r_match["bid"]))
                    bid = int(r_match["bid"])

                    if bmap:
                        # parse mode_vn int from regex
                        if r_match["mode_vn"] is not None:
                            mode_vn = {"Taiko": 1, "CatchTheBeat": 2, "osu!mania": 3}[
                                r_match["mode_vn"]
                            ]
                        else:
                            # use player mode if not specified
                            mode_vn = player.status.mode

                        # parse the mods from regex
                        mods = None
                        if r_match["mods"] is not None:
                            mods = Mods.from_np(r_match["mods"][1:], mode_vn)

                        player.last_np = {
                            "bmap": bmap,
                            "bid": bid,
                            "mode_vn": mode_vn,
                            "mods": mods,
                            "timeout": time.time() + 300,  # /np's last 5mins
                        }

                        # calculate generic pp values from their /np

                        osu_file_available = await ensure_osu_file_is_available(
                            bmap.id,
                            expected_md5=bmap.md5,
                        )
                        if not osu_file_available:
                            resp_msg = (
                                "Mapfile could not be found; "
                                "this incident has been reported."
                            )
                        else:
                            # calculate pp for common generic values
                            pp_calc_st = time.time_ns()

                            mods = None
                            if r_match["mods"] is not None:
                                # [1:] to remove leading whitespace
                                mods_str = r_match["mods"][1:]
                                mods = Mods.from_np(mods_str, mode_vn)

                            scores = [
                                ScoreParams(
                                    mode=mode_vn,
                                    mods=int(mods) if mods else None,
                                    acc=acc,
                                )
                                for acc in app.settings.PP_CACHED_ACCURACIES
                            ]

                            results = (
                                await app.usecases.performance.calculate_performances(
                                    beatmap_id=bmap.id,
                                    scores=scores,
                                )
                            )

                            resp_msg = " | ".join(
                                f"{acc}%: {result['performance']['pp']:,.2f}pp"
                                for acc, result in zip(
                                    app.settings.PP_CACHED_ACCURACIES,
                                    results,
                                )
                            )

                            elapsed = time.time_ns() - pp_calc_st
                            resp_msg += f" | Elapsed: {magnitude_fmt_time(elapsed)}"
                    else:
                        resp_msg = "Could not find map."

                        # time out their previous /np
                        player.last_np = None

                    player.send(resp_msg, sender=target)
                else:
                    # Not a command and not an np. Generate an AI response.
                    async def send_ai_resp() -> None:
                        ai_resp = await fetch_bot_response(msg)
                        if ai_resp:
                            player.send(ai_resp, sender=target)

                    asyncio.create_task(send_ai_resp())

        player.update_latest_activity_soon()

        log(f"{player} @ {target}: {msg}", Ansi.LCYAN)
        with open(DISK_CHAT_LOG_FILE, "a+") as f:
            f.write(
                f"[{get_timestamp(full=True, tz=ZoneInfo('GMT'))}] {player} @ {target}: {msg}\n",
            )
