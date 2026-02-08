from __future__ import annotations

import app
from app.api.packets.constants import IGNORED_CHANNELS
from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class ChannelPart(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.name = reader.read_string()

    async def handle(self, player):
        if self.name in IGNORED_CHANNELS:
            return
        channel = app.state.sessions.channels.get_by_name(self.name)

        if not channel:
            log(f"{player} failed to leave {self.name}.")
            return

        if player not in channel:
            return

        player.leave_channel(channel)
