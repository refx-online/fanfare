from __future__ import annotations

from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.state import sessions


class FriendAdd(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.user_id = reader.read_i32()

    async def handle(self, player):
        target = sessions.players.get(id=self.user_id)
        if not target:
            log(f"{player} tried to add a user who is not online! ({self.user_id})")
            return
        if target is sessions.bot:
            return
        if target.id in player.blocks:
            player.blocks.remove(target.id)
        player.update_latest_activity_soon()
        await player.add_friend(target)
