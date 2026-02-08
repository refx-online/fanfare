from __future__ import annotations

from app.logging import Ansi
from app.logging import log
from app.objects.match import SlotStatus
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchChangeSlot(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.slot_id = reader.read_i32()

    async def handle(self, player) -> None:
        if player.match is None:
            return

        # read new slot ID
        if not 0 <= self.slot_id < 16:
            return

        if player.match.slots[self.slot_id].status != SlotStatus.open:
            log(f"{player} tried to move into non-open slot.", Ansi.LYELLOW)
            return

        # swap with current slot.
        slot = player.match.get_slot(player)
        assert slot is not None

        player.match.slots[self.slot_id].copy_from(slot)
        slot.reset()

        player.match.enqueue_state()  # technically not needed for host?
