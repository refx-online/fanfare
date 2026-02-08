from __future__ import annotations

import app
from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchInvite(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.user_id = reader.read_i32()

    async def handle(self, player) -> None:
        if not player.match:
            return

        target = app.state.sessions.players.get(id=self.user_id)
        if not target:
            log(f"{player} tried to invite a user who is not online! ({self.user_id})")
            return

        if target is app.state.sessions.bot:
            player.send_bot("I'm too busy!")
            return

        target.enqueue(app.packets.match_invite(player, target.name))
        player.update_latest_activity_soon()

        log(f"{player} invited {target} to their match.")
