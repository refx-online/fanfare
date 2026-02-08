from __future__ import annotations

from app.logging import Ansi
from app.logging import log
from app.objects.match import SlotStatus
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchLock(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.slot_id = reader.read_i32()

    async def handle(self, player) -> None:
        if player.match is None:
            return

        if player is not player.match.host:
            log(f"{player} attempted to lock match as non-host.", Ansi.LYELLOW)
            return

        # read new slot ID
        if not 0 <= self.slot_id < 16:
            return

        slot = player.match.slots[self.slot_id]

        if slot.status == SlotStatus.locked:
            slot.status = SlotStatus.open
        else:
            if slot.player is player.match.host:
                # don't allow the match host to kick
                # themselves by clicking their crown
                return

            if slot.player:
                # uggggggh i hate trusting the osu! client
                # man why is it designed like this
                # TODO: probably going to end up changing
                ...  # slot.reset()

            slot.status = SlotStatus.locked

        player.match.enqueue_state()
