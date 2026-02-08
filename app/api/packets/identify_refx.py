from __future__ import annotations

from app.packets import BanchoPacketReader
from app.packets import BasePacket


class IdentifyRefx(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        # cheat: 1/2
        # cheatcheat: 5/6
        self.current_lb = reader.read_i32()

    async def handle(self, player):
        # TODO: should i separate this to a different packet?
        # since this shit is really getting frequently called
        player.refx = True

        # HACK: current me doesn't know how to handle cheat checking, so i do this
        # for future me: FIXME!
        player.refx_lb = self.current_lb
