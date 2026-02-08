from __future__ import annotations

from app.objects.match import MatchTeams
from app.packets import BasePacket


class MatchChangeTeam(BasePacket):
    async def handle(self, player):
        match = player.match
        if match is None:
            return

        slot = match.get_slot(player)
        assert slot is not None

        if slot.team == MatchTeams.blue:
            slot.team = MatchTeams.red
        else:
            slot.team = MatchTeams.blue

        match.enqueue_state(lobby=False)
