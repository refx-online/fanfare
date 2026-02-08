from __future__ import annotations

from app.objects.match import SlotStatus
from app.packets import BasePacket


class MatchNotReady(BasePacket):
    async def handle(self, player):
        match = player.match
        if match is None:
            return

        slot = match.get_slot(player)
        assert slot is not None

        slot.status = SlotStatus.not_ready

        match.enqueue_state()
