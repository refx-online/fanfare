from __future__ import annotations

import time
from zoneinfo import ZoneInfo

import app
from app.api.packets.constants import DISK_CHAT_LOG_FILE
from app.api.packets.constants import IGNORED_CHANNELS
from app.api.packets.constants import NOW_PLAYING_RGX
from app.logging import Ansi
from app.logging import get_timestamp
from app.logging import log
from app.objects.beatmap import Beatmap
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class SendMessage(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.msg = reader.read_message()

    async def handle(self, player) -> None:
        if player.silenced:
            log(f"{player} sent a message while silenced.", Ansi.LYELLOW)
            return

        # remove leading/trailing whitespace
        msg = self.msg.text.strip()

        if not msg:
            return

        recipient = self.msg.recipient

        if recipient in IGNORED_CHANNELS:
            return
        elif recipient == "#spectator":
            if player.spectating:
                spec_id = player.spectating.id
            elif player.spectators:
                spec_id = player.id
            else:
                return
            t_chan = app.state.sessions.channels.get_by_name(f"#spec_{spec_id}")
        elif recipient == "#multiplayer":
            if not player.match:
                return
            t_chan = player.match.chat
        else:
            t_chan = app.state.sessions.channels.get_by_name(recipient)

        if not t_chan:
            log(f"{player} wrote to non-existent {recipient}.", Ansi.LYELLOW)
            return

        if player not in t_chan:
            log(f"{player} wrote to {recipient} without being in it.")
            return

        if not t_chan.can_write(player.priv):
            log(f"{player} wrote to {recipient} with insufficient privileges.")
            return

        if len(msg) > 2000:
            msg = f"{msg[:2000]}... (truncated)"
            player.enqueue(
                app.packets.notification(
                    "Your message was truncated\n(exceeded 2000 characters).",
                ),
            )

        if msg.startswith(app.settings.COMMAND_PREFIX):
            cmd = await app.commands.process_commands(player, t_chan, msg)
        else:
            cmd = None

        if cmd:
            if not cmd["hidden"]:
                t_chan.send(msg, sender=player)
                if cmd["resp"] is not None:
                    t_chan.send_bot(cmd["resp"])
            else:
                staff = app.state.sessions.players.staff
                t_chan.send_selective(
                    msg=msg,
                    sender=player,
                    recipients=staff - {player},
                )
                if cmd["resp"] is not None:
                    t_chan.send_selective(
                        msg=cmd["resp"],
                        sender=app.state.sessions.bot,
                        recipients=staff | {player},
                    )
        else:
            r_match = NOW_PLAYING_RGX.match(msg)
            if r_match:
                bmap = await Beatmap.from_bid(int(r_match["bid"]))
                bid = int(r_match["bid"])
                if bmap:
                    if r_match["mode_vn"] is not None:
                        mode_vn = {"Taiko": 1, "CatchTheBeat": 2, "osu!mania": 3}[
                            r_match["mode_vn"]
                        ]
                    else:
                        mode_vn = player.status.mode
                    mods = None
                    if r_match["mods"] is not None:
                        mods = app.constants.mods.Mods.from_np(
                            r_match["mods"][1:],
                            mode_vn,
                        )
                    player.last_np = {
                        "bmap": bmap,
                        "bid": bid,
                        "mods": mods,
                        "mode_vn": mode_vn,
                        "timeout": time.time() + 300,
                    }
                else:
                    player.last_np = None
            t_chan.send(msg, sender=player)

        player.update_latest_activity_soon()

        log(f"{player} @ {t_chan}: {msg}", Ansi.LCYAN)

        with open(DISK_CHAT_LOG_FILE, "a+") as f:
            f.write(
                f"[{get_timestamp(full=True, tz=ZoneInfo('GMT'))}] {player} @ {t_chan}: {msg}\n",
            )
