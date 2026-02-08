from __future__ import annotations

from app.logging import Ansi
from app.logging import log
from app.objects.player import Player
from app.packets import BasePacket


class StopSpectating(BasePacket):
    async def handle(self, player: Player) -> None:
        host = player.spectating
        if not host:
            log(f"{player} tried to stop spectating when they're not..?", Ansi.LRED)
            return

        host.remove_spectator(player)
