from __future__ import annotations

import app
from app.packets import BasePacket


class MatchFailed(BasePacket):
    async def handle(self, player) -> None:
        if player.match is None:
            return

        # find the player's slot id, and enqueue that
        # they've failed to all other players in the match.
        slot_id = player.match.get_slot_id(player)
        assert slot_id is not None

        player.match.enqueue(app.packets.match_player_failed(slot_id), lobby=False)
