from __future__ import annotations

import app
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class UserPresenceRequestAll(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.ingame_time = reader.read_i32()

    async def handle(self, player) -> None:
        # NOTE: this packet is only used when there
        # are >256 players visible to the client.

        buffer = bytearray()

        for player in app.state.sessions.players.unrestricted:
            buffer += app.packets.user_presence(player)

        player.enqueue(bytes(buffer))
