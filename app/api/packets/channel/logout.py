"""Packet logic for Bancho API: Logout packet handler."""

from __future__ import annotations

import time

from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class Logout(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        reader.read_i32()  # reserved

    async def handle(self, player: Player) -> None:
        if (time.time() - player.login_time) < 1:
            # osu! has a weird tendency to log out immediately after login.
            # block any logout request within 1 second from login.
            return

        player.logout()
        player.update_latest_activity_soon()
