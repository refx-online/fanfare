"""Packet logic for Bancho API: LobbyPart packet handler."""

from __future__ import annotations

from app.objects.player import Player
from app.packets import BasePacket


class LobbyPart(BasePacket):
    async def handle(self, player: Player) -> None:
        player.in_lobby = False
