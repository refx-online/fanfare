from __future__ import annotations

import app
from app.logging import Ansi
from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchChangePassword(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.match_data = reader.read_match()

    async def handle(self, player) -> None:
        if not app.packets.validate_match_data(
            self.match_data,
            expected_host_id=player.id,
        ):
            log(
                f"{player} tried to change match password with invalid data.",
                Ansi.LYELLOW,
            )
            return

        if player.match is None:
            return

        if player is not player.match.host:
            log(f"{player} attempted to change pw as non-host.", Ansi.LYELLOW)
            return

        player.match.passwd = self.match_data.passwd
        player.match.enqueue_state()
