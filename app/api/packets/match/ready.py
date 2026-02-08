from __future__ import annotations

from app.objects.match import SlotStatus
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchReady(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.slot_id = reader.read_u8()

    async def handle(self, player):
        match = player.match
        if not match:
            return
        if self.slot_id >= len(match.slots):
            return
        slot = match.slots[self.slot_id]
        if slot.player != player:
            return
        slot.status = SlotStatus.ready
        match.enqueue_state()
        player.update_latest_activity_soon()
