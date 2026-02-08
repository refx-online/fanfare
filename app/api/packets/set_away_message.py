from __future__ import annotations

from app.packets import BanchoPacketReader
from app.packets import BasePacket


class SetAwayMessage(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.msg = reader.read_message()

    async def handle(self, player):
        player.away_msg = self.msg.text
