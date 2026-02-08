from __future__ import annotations

import app
from app.logging import log
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchJoin(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.match_id = reader.read_i32()
        self.match_passwd = reader.read_string()

    async def handle(self, player: Player) -> None:
        match = app.state.sessions.matches[self.match_id]
        if not match:
            log(f"{player} tried to join a non-existant mp lobby?")
            player.enqueue(app.packets.match_join_fail())
            return

        if player.restricted:
            player.enqueue(
                app.packets.match_join_fail()
                + app.packets.notification(
                    "Multiplayer is not available while restricted.",
                ),
            )
            return

        if player.silenced:
            player.enqueue(
                app.packets.match_join_fail()
                + app.packets.notification(
                    "Multiplayer is not available while silenced.",
                ),
            )
            return

        player.update_latest_activity_soon()
        player.join_match(match, self.match_passwd)
