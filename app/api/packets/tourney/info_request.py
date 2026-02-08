from __future__ import annotations

from app import packets
from app.constants.privileges import Privileges
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.state import sessions


class TourneyMatchInfoRequest(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.match_id = reader.read_i32()

    async def handle(self, player):
        if not 0 <= self.match_id < 64:
            return  # invalid match id

        if not player.priv & Privileges.DONATOR:
            return  # insufficient privs

        match = sessions.matches[self.match_id]
        if not match:
            return  # match not found

        player.enqueue(packets.update_match(match, send_pw=False))
