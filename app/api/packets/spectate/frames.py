from __future__ import annotations

import struct

import app
from app.objects.player import Player
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class SpectateFrames(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        try:
            self.frame_bundle = reader.read_replayframe_bundle()
        except:  # might happen because of "old client"
            self.frame_bundle = reader.read_raw()

    async def handle(self, player: Player) -> None:
        if not isinstance(self.frame_bundle, app.packets.ReplayFrameBundle):
            for spectator in player.spectators:
                spectator.enqueue(app.packets.spectate_frames(self.frame_bundle))

            return

        # TODO: perform validations on the parsed frame bundle
        # to ensure it's not being tamperated with or weaponized.

        # NOTE: this is given a fastpath here for efficiency due to the
        # sheer rate of usage of these packets in spectator mode.

        data = (
            struct.pack("<HxI", 15, len(self.frame_bundle.raw_data))
            + self.frame_bundle.raw_data
        )

        for spectator in player.spectators:
            spectator.enqueue(data)
