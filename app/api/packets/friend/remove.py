from __future__ import annotations

from app.logging import log
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.state import sessions


class FriendRemove(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.user_id = reader.read_i32()

    async def handle(self, player):
        target = sessions.players.get(id=self.user_id)
        if not target:
            log(f"{player} tried to remove a user who is not online! ({self.user_id})")
            return
        if target is sessions.bot:
            return
        player.update_latest_activity_soon()
        await player.remove_friend(target)
