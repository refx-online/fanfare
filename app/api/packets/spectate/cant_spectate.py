from __future__ import annotations

import app
from app.logging import Ansi
from app.logging import log
from app.objects.player import Player
from app.packets import BasePacket


class CantSpectate(BasePacket):
    async def handle(self, player: Player) -> None:
        if not player.spectating:
            log(f"{player} sent can't spectate while not spectating?", Ansi.LRED)
            return

        if not player.stealth:
            data = app.packets.spectator_cant_spectate(player.id)
            host = player.spectating
            host.enqueue(data)

            for t in host.spectators:
                t.enqueue(data)
