from __future__ import annotations

import app
from app.logging import Ansi
from app.logging import log
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class StartSpectating(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.target_id = reader.read_i32()

    async def handle(self, player: Player) -> None:
        new_host = app.state.sessions.players.get(id=self.target_id)
        if not new_host:
            log(
                f"{player} tried to spectate nonexistant id {self.target_id}.",
                Ansi.LYELLOW,
            )
            return

        current_host = player.spectating
        if current_host:
            if current_host == new_host:
                # host hasn't changed, they didn't have
                # the map but have downloaded it.
                if not player.stealth:
                    # NOTE: `player` would have already received the other
                    # fellow spectators, so no need to resend them.
                    new_host.enqueue(app.packets.spectator_joined(player.id))
                    player_joined = app.packets.fellow_spectator_joined(player.id)
                    for spec in new_host.spectators:
                        if spec is not player:
                            spec.enqueue(player_joined)
                return
            current_host.remove_spectator(player)

        new_host.add_spectator(player)
