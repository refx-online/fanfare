from __future__ import annotations

from app import packets
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.state import sessions


class StatsRequest(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.user_ids = reader.read_i32_list_i16l()

    async def handle(self, player):
        unrestrcted_ids = [p.id for p in sessions.players.unrestricted]
        is_online = lambda o: o in unrestrcted_ids and o != player.id

        for online in filter(is_online, self.user_ids):
            target = sessions.players.get(id=online)
            if target:
                if target is sessions.bot:
                    packet = packets.bot_stats(target)
                else:
                    packet = packets.user_stats(target)
                player.enqueue(packet)
