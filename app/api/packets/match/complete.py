from __future__ import annotations

import asyncio

import app
from app.objects.match import SlotStatus
from app.packets import BasePacket


class MatchComplete(BasePacket):
    async def handle(self, player) -> None:
        if player.match is None:
            return

        slot = player.match.get_slot(player)
        assert slot is not None

        slot.status = SlotStatus.complete

        # check if there are any players that haven't finished.
        if any([s.status == SlotStatus.playing for s in player.match.slots]):
            return

        # find any players just sitting in the multi room
        # that have not been playing the map; they don't
        # need to know all the players have completed, only
        # the ones who are playing (just new match info).
        not_playing = [
            s.player.id
            for s in player.match.slots
            if s.player is not None and s.status != SlotStatus.complete
        ]

        was_playing = [
            s for s in player.match.slots if s.player and s.player.id not in not_playing
        ]

        player.match.unready_players(expected=SlotStatus.complete)
        player.match.reset_players_loaded_status()

        player.match.in_progress = False
        player.match.enqueue(
            app.packets.match_complete(),
            lobby=False,
            immune=not_playing,
        )
        player.match.enqueue_state()

        if player.match.is_scrimming:
            # determine winner, update match points & inform players.
            asyncio.create_task(player.match.update_matchpoints(was_playing))
