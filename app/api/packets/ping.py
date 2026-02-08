from __future__ import annotations

from app.packets import BasePacket


class Ping(BasePacket):
    async def handle(self, player) -> None:
        pass  # ping be like
