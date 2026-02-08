from __future__ import annotations

from app.packets import BanchoPacketReader
from app.packets import BasePacket


class ToggleBlockingDMs(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.value = reader.read_i32()

    async def handle(self, player):
        player.pm_private = self.value == 1
        player.update_latest_activity_soon()
