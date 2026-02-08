from __future__ import annotations

import app
from app.objects.match import Slot
from app.objects.match import SlotStatus
from app.packets import BasePacket


def is_playing(slot: Slot) -> bool:
    return slot.status == SlotStatus.playing and not slot.loaded


class MatchLoadComplete(BasePacket):
    async def handle(self, player) -> None:
        if player.match is None:
            return

        # our player has loaded in and is ready to play.
        slot = player.match.get_slot(player)
        assert slot is not None

        slot.loaded = True

        # check if all players are loaded,
        # if so, tell all players to begin.
        if not any(map(is_playing, player.match.slots)):
            player.match.enqueue(app.packets.match_all_players_loaded(), lobby=False)
