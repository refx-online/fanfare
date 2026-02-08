from __future__ import annotations

from app.logging import log
from app.objects.player import PresenceFilter
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class ReceiveUpdates(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.value = reader.read_i32()

    async def handle(self, player):
        if not 0 <= self.value < 3:
            log(f"{player} tried to set his presence filter to {self.value}?")
            return

        player.pres_filter = PresenceFilter(self.value)
