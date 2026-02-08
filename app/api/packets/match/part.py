"""Packet logic for Bancho API: MatchPart packet handler."""

from __future__ import annotations

from app.objects.player import Player
from app.packets import BasePacket


class MatchPart(BasePacket):
    async def handle(self, player: Player) -> None:
        player.update_latest_activity_soon()
        player.leave_match()
