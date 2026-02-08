from __future__ import annotations

import app
from app.logging import Ansi
from app.logging import log
from app.objects.player import Player
from app.packets import BasePacket


class LobbyJoin(BasePacket):
    async def handle(self, player: Player) -> None:
        player.in_lobby = True

        for match in app.state.sessions.matches:
            if match is not None:
                try:
                    player.enqueue(app.packets.new_match(match))
                except ValueError:
                    log(
                        f"Failed to send match {match.id} to player joining lobby; likely due to missing host",
                        Ansi.LYELLOW,
                    )
                    stacktrace = app.utils.get_appropriate_stacktrace()
                    await app.state.services.log_strange_occurrence(stacktrace)
                    continue
