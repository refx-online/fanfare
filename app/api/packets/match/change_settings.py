from __future__ import annotations

import app
from app.api.packets.constants import BASE_DOMAIN
from app.constants.gamemodes import GameMode
from app.constants.mods import SPEED_CHANGING_MODS
from app.constants.mods import Mods
from app.logging import Ansi
from app.logging import log
from app.objects.beatmap import Beatmap
from app.objects.match import MatchTeams
from app.objects.match import MatchTeamTypes
from app.objects.match import MatchWinConditions
from app.objects.match import SlotStatus
from app.packets import BanchoPacketReader
from app.packets import BasePacket


class MatchChangeSettings(BasePacket):
    def __init__(self, reader: BanchoPacketReader) -> None:
        self.match_data = reader.read_match()

    async def handle(self, player) -> None:
        if not app.packets.validate_match_data(
            self.match_data,
            expected_host_id=player.id,
        ):
            log(
                f"{player} tried to change match settings with invalid data.",
                Ansi.LYELLOW,
            )
            return

        if player.match is None:
            return

        if player is not player.match.host:
            log(f"{player} attempted to change settings as non-host.", Ansi.LYELLOW)
            return

        if self.match_data.freemods != player.match.freemods:
            # freemods status has been changed.
            player.match.freemods = self.match_data.freemods

            if self.match_data.freemods:
                # match mods -> active slot mods.
                for slot in player.match.slots:
                    if slot.player is not None:
                        # the slot takes any non-speed
                        # changing mods from the match.
                        slot.mods = player.match.mods & ~SPEED_CHANGING_MODS

                # keep only speed-changing mods.
                player.match.mods &= SPEED_CHANGING_MODS
            else:
                # host mods -> match mods.
                host = player.match.get_host_slot()  # should always exist
                assert host is not None

                # the match keeps any speed-changing mods,
                # and also takes any mods the host has enabled.
                player.match.mods &= SPEED_CHANGING_MODS
                player.match.mods |= host.mods

                for slot in player.match.slots:
                    if slot.player is not None:
                        slot.mods = Mods.NOMOD

        if self.match_data.map_id == -1:
            # map being changed, unready players.
            player.match.unready_players(expected=SlotStatus.ready)
            player.match.prev_map_id = player.match.map_id

            player.match.map_id = -1
            player.match.map_md5 = ""
            player.match.map_name = ""
        elif player.match.map_id == -1:
            if player.match.prev_map_id != self.match_data.map_id:
                # new map has been chosen, send to match chat.
                map_url = f"https://osu.{BASE_DOMAIN}/b/{self.match_data.map_id}"
                map_embed = f"[{map_url} {self.match_data.map_name}]"
                player.match.chat.send_bot(f"Selected: {map_embed}.")

            # use our serverside version if we have it, but
            # still allow for users to pick unknown maps.
            bmap = await Beatmap.from_md5(self.match_data.map_md5)

            if bmap:
                player.match.map_id = bmap.id
                player.match.map_md5 = bmap.md5
                player.match.map_name = bmap.full_name
                player.match.mode = GameMode(player.match.host.status.mode)
            else:
                player.match.map_id = self.match_data.map_id
                player.match.map_md5 = self.match_data.map_md5
                player.match.map_name = self.match_data.map_name
                player.match.mode = GameMode(self.match_data.mode)

        if player.match.team_type != self.match_data.team_type:
            # if theres currently a scrim going on, only allow
            # team type to change by using the !mp teams command.
            if player.match.is_scrimming:
                _team = ("head-to-head", "tag-coop", "team-vs", "tag-team-vs")[
                    self.match_data.team_type
                ]

                msg = (
                    "Changing team type while scrimming will reset "
                    "the overall score - to do so, please use the "
                    f"!mp teams {_team} command."
                )
                player.match.chat.send_bot(msg)
            else:
                # find the new appropriate default team.
                # defaults are (ffa: neutral, teams: red).
                if self.match_data.team_type in (
                    MatchTeamTypes.head_to_head,
                    MatchTeamTypes.tag_coop,
                ):
                    new_t = MatchTeams.neutral
                else:
                    new_t = MatchTeams.red

                # change each active slots team to
                # fit the correspoding team type.
                for slot in player.match.slots:
                    if slot.player is not None:
                        slot.team = new_t

                # change the matches'.
                player.match.team_type = MatchTeamTypes(self.match_data.team_type)

        if player.match.win_condition != self.match_data.win_condition:
            # win condition changing; if `use_pp_scoring`
            # is enabled, disable it. always use new cond.
            if player.match.use_pp_scoring:
                player.match.use_pp_scoring = False

            player.match.win_condition = MatchWinConditions(
                self.match_data.win_condition,
            )

        player.match.name = self.match_data.name

        player.match.enqueue_state()
