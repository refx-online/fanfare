from __future__ import annotations

import app
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class UserPresenceRequest(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.user_ids = reader.read_i32_list_i16l()

    async def handle(self, player) -> None:
        for pid in self.user_ids:
            target = app.state.sessions.players.get(id=pid)
            if target:
                if target is app.state.sessions.bot:
                    # optimization for bot since it's
                    # the most frequently requested user
                    packet = app.packets.bot_presence(target)
                else:
                    packet = app.packets.user_presence(target)

                player.enqueue(packet)
