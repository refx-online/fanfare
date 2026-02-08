from __future__ import annotations

import app
from app.constants.gamemodes import GameMode
from app.constants.mods import Mods
from app.logging import Ansi
from app.logging import log
from app.objects.channel import Channel
from app.objects.match import Match
from app.objects.match import MatchTeamTypes
from app.objects.match import MatchWinConditions
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchCreate(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.match_data = reader.read_match()

    async def handle(self, player) -> None:
        if not app.packets.validate_match_data(
            self.match_data,
            expected_host_id=player.id,
        ):
            log(f"{player} tried to create a match with invalid data.", Ansi.LYELLOW)
            return

        if player.restricted:
            player.enqueue(
                app.packets.match_join_fail()
                + app.packets.notification(
                    "Multiplayer is not available while restricted.",
                ),
            )
            return

        if player.silenced:
            player.enqueue(
                app.packets.match_join_fail()
                + app.packets.notification(
                    "Multiplayer is not available while silenced.",
                ),
            )
            return

        match_id = app.state.sessions.matches.get_free()

        if match_id is None:
            # failed to create match (match slots full).
            player.send_bot("Failed to create match (no slots available).")
            player.enqueue(app.packets.match_join_fail())
            return

        # create the channel and add it
        # to the global channel list as
        # an instanced channel.
        chat_channel = Channel(
            name=f"#multi_{match_id}",
            topic=f"MID {match_id}'s multiplayer channel.",
            auto_join=False,
            instance=True,
        )

        match = Match(
            id=match_id,
            name=self.match_data.name,
            password=self.match_data.passwd.removesuffix("//private"),
            has_public_history=not self.match_data.passwd.endswith("//private"),
            map_name=self.match_data.map_name,
            map_id=self.match_data.map_id,
            map_md5=self.match_data.map_md5,
            host_id=self.match_data.host_id,
            mode=GameMode(self.match_data.mode),
            mods=Mods(self.match_data.mods),
            win_condition=MatchWinConditions(self.match_data.win_condition),
            team_type=MatchTeamTypes(self.match_data.team_type),
            freemods=bool(self.match_data.freemods),
            seed=self.match_data.seed,
            chat_channel=chat_channel,
        )

        app.state.sessions.matches[match_id] = match
        app.state.sessions.channels.append(chat_channel)
        match.chat = chat_channel

        player.update_latest_activity_soon()
        player.join_match(match, self.match_data.passwd)

        match.chat.send_bot(f"Match created by {player.name}.")
        log(f"{player} created a new multiplayer match.")
