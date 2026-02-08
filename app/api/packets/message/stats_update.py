from __future__ import annotations

import app
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class StatsRequest(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.user_ids = reader.read_i32_list_i16l()

    async def handle(self, player: Player) -> None:
        unrestrcted_ids = [p.id for p in app.state.sessions.players.unrestricted]
        is_online = lambda o: o in unrestrcted_ids and o != player.id

        for online in filter(is_online, self.user_ids):
            target = app.state.sessions.players.get(id=online)
            if target:
                if target is app.state.sessions.bot:
                    # optimization for bot since it's
                    # the most frequently requested user
                    packet = app.packets.bot_stats(target)
                else:
                    packet = app.packets.user_stats(target)

                player.enqueue(packet)
