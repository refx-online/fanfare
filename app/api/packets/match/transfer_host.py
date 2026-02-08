from __future__ import annotations

import app
from app.logging import Ansi
from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchTransferHost(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.slot_id = reader.read_i32()

    async def handle(self, player) -> None:
        if player.match is None:
            return

        if player is not player.match.host:
            log(f"{player} attempted to transfer host as non-host.", Ansi.LYELLOW)
            return

        # read new slot ID
        if not 0 <= self.slot_id < 16:
            return

        target = player.match.slots[self.slot_id].player
        if not target:
            log(f"{player} tried to transfer host to an empty slot?")
            return

        player.match.host_id = target.id
        player.match.host.enqueue(app.packets.match_transfer_host())
        player.match.enqueue_state()
