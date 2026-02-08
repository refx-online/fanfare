from __future__ import annotations

import app
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class IdentifyAeris(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.features = reader.read_i32()

    async def handle(self, player):
        player.enqueue(app.packets.identify_aeris(1 << 1))  # cheats
        player.aeris = True
