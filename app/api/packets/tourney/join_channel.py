from __future__ import annotations

from app.constants.privileges import Privileges
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.state import sessions


class TourneyMatchJoinChannel(BasePacket):
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

        for slot in match.slots:
            if slot.player is not None:
                if player.id == slot.player.id:
                    return  # playing in the match

        # attempt to join match chan
        if player.join_channel(match.chat):
            match.tourney_clients.add(player.id)
