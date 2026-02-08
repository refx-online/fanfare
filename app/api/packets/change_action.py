from __future__ import annotations

import app
from app.constants.gamemodes import GameMode
from app.constants.mods import Mods
from app.objects.player import Action
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class ChangeAction(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.action = reader.read_u8()
        self.info_text = reader.read_string()
        self.map_md5 = reader.read_string()

        self.mods = reader.read_u32()
        self.mode = reader.read_u8()

        self.map_id = reader.read_i32()

    async def handle(self, player: Player) -> None:
        # update the user's status.
        player.status.action = Action(self.action)
        player.status.info_text = player.resolve_info_text(self.info_text)
        player.status.map_md5 = self.map_md5

        mode, mods = player.resolve_mode(self.mode, self.mods)

        player.status.mods = Mods(mods)
        player.status.mode = GameMode(mode)

        player.status.map_id = self.map_id

        # broadcast it to all online players.
        if not player.restricted:
            app.state.sessions.players.enqueue(app.packets.user_stats(player))
