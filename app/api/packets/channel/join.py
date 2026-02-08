from __future__ import annotations

import app
from app.api.packets.constants import IGNORED_CHANNELS
from app.logging import Ansi
from app.logging import log
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class ChannelJoin(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.name = reader.read_string()

    async def handle(self, player: Player) -> None:
        if self.name in IGNORED_CHANNELS:
            return

        channel = app.state.sessions.channels.get_by_name(self.name)

        if not channel or not player.join_channel(channel):
            log(f"{player} failed to join {self.name}.", Ansi.LYELLOW)
            return
