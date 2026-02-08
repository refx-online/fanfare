from __future__ import annotations

from app.objects.match import SlotStatus
from app.packets import BasePacket


class MatchNoBeatmap(BasePacket):
    async def handle(self, player):
        match = player.match
        if match is None:
            return

        slot = match.get_slot(player)
        assert slot is not None

        slot.status = SlotStatus.no_map

        match.enqueue_state(lobby=False)
