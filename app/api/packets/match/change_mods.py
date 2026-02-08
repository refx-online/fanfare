from __future__ import annotations

from app.constants.mods import SPEED_CHANGING_MODS
from app.constants.mods import Mods
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchChangeMods(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.mods = reader.read_i32()

    async def handle(self, player):
        match = player.match
        if match is None:
            return
        if match.freemods:
            if player is match.host:
                match.mods = Mods(self.mods & SPEED_CHANGING_MODS)
            slot = match.get_slot(player)
            assert slot is not None
            slot.mods = Mods(self.mods & ~SPEED_CHANGING_MODS)
        else:
            if player is not match.host:
                # log attempt if needed
                return
            match.mods = Mods(self.mods)
        match.enqueue_state()
