from __future__ import annotations

import app
from app.objects.match import SlotStatus
from app.packets import BasePacket


class MatchSkipRequest(BasePacket):
    async def handle(self, player):
        match = player.match
        if match is None:
            return

        slot = match.get_slot(player)
        assert slot is not None

        slot.skipped = True
        match.enqueue(app.packets.match_player_skipped(player.id))
        for slot in match.slots:
            if slot.status == SlotStatus.playing and not slot.skipped:
                return

        match.enqueue(app.packets.match_skip(), lobby=False)
