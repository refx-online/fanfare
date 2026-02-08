from __future__ import annotations

from app.packets import BasePacket


class MatchStart(BasePacket):
    async def handle(self, player):
        match = player.match
        if not match:
            return

        if match.host != player:
            return

        match.start()
        match.enqueue_state()
        player.update_latest_activity_soon()
