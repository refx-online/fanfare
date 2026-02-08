from __future__ import annotations

import app
from app.api.packets.change_action import ChangeAction
from app.api.packets.channel.join import ChannelJoin
from app.api.packets.channel.logout import Logout
from app.api.packets.channel.part import ChannelPart
from app.api.packets.channel.send_message import SendMessage
from app.api.packets.identify_aeris import IdentifyAeris
from app.api.packets.identify_refx import IdentifyRefx
from app.api.packets.match.change_mods import MatchChangeMods
from app.api.packets.match.change_password import MatchChangePassword
from app.api.packets.match.change_settings import MatchChangeSettings
from app.api.packets.match.change_slot import MatchChangeSlot
from app.api.packets.match.change_team import MatchChangeTeam
from app.api.packets.match.complete import MatchComplete
from app.api.packets.match.create import MatchCreate
from app.api.packets.match.failed import MatchFailed
from app.api.packets.match.has_beatmap import MatchHasBeatmap
from app.api.packets.match.invite import MatchInvite
from app.api.packets.match.join import MatchJoin
from app.api.packets.match.join_lobby import LobbyJoin
from app.api.packets.match.load_complete import MatchLoadComplete
from app.api.packets.match.lock import MatchLock
from app.api.packets.match.no_beatmap import MatchNoBeatmap
from app.api.packets.match.not_ready import MatchNotReady
from app.api.packets.match.part import MatchPart
from app.api.packets.match.part_lobby import LobbyPart
from app.api.packets.match.ready import MatchReady
from app.api.packets.match.score_update import MatchScoreUpdate
from app.api.packets.match.skip_request import MatchSkipRequest
from app.api.packets.match.start import MatchStart
from app.api.packets.match.transfer_host import MatchTransferHost
from app.api.packets.message.send_private import SendPrivateMessage
from app.api.packets.ping import Ping
from app.api.packets.receive_updates import ReceiveUpdates
from app.api.packets.set_away_message import SetAwayMessage
from app.api.packets.spectate.cant_spectate import CantSpectate
from app.api.packets.spectate.frames import SpectateFrames
from app.api.packets.spectate.start import StartSpectating
from app.api.packets.spectate.stop import StopSpectating
from app.api.packets.toggle_block_non_friend_dms import ToggleBlockingDMs
from app.api.packets.tourney.info_request import TourneyMatchInfoRequest
from app.api.packets.tourney.join_channel import TourneyMatchJoinChannel
from app.api.packets.tourney.leave_channel import TourneyMatchLeaveChannel
from app.api.packets.user_presence_request import UserPresenceRequest
from app.api.packets.user_presence_request_all import UserPresenceRequestAll
from app.api.packets.user_stats_request import StatsRequest
from app.packets import ClientPackets

for packet, handler in (
    (ClientPackets.PING, Ping),
    (ClientPackets.CHANGE_ACTION, ChangeAction),
    (ClientPackets.RECEIVE_UPDATES, ReceiveUpdates),
    (ClientPackets.SET_AWAY_MESSAGE, SetAwayMessage),
    (ClientPackets.USER_STATS_REQUEST, StatsRequest),
    (ClientPackets.USER_PRESENCE_REQUEST, UserPresenceRequest),
    (ClientPackets.USER_PRESENCE_REQUEST_ALL, UserPresenceRequestAll),
    (ClientPackets.TOGGLE_BLOCK_NON_FRIEND_DMS, ToggleBlockingDMs),
    (ClientPackets.REFX_LB, IdentifyRefx),
    (ClientPackets.IDENTIFY_AERIS, IdentifyAeris),
    (ClientPackets.SEND_PUBLIC_MESSAGE, SendMessage),
    (ClientPackets.SEND_PRIVATE_MESSAGE, SendPrivateMessage),
    (ClientPackets.CHANNEL_JOIN, ChannelJoin),
    (ClientPackets.CHANNEL_PART, ChannelPart),
    (ClientPackets.LOGOUT, Logout),
    (ClientPackets.JOIN_LOBBY, LobbyJoin),
    (ClientPackets.PART_LOBBY, LobbyPart),
    (ClientPackets.CREATE_MATCH, MatchCreate),
    (ClientPackets.JOIN_MATCH, MatchJoin),
    (ClientPackets.PART_MATCH, MatchPart),
    (ClientPackets.MATCH_CHANGE_SLOT, MatchChangeSlot),
    (ClientPackets.MATCH_READY, MatchReady),
    (ClientPackets.MATCH_LOCK, MatchLock),
    (ClientPackets.MATCH_CHANGE_SETTINGS, MatchChangeSettings),
    (ClientPackets.MATCH_START, MatchStart),
    (ClientPackets.MATCH_SCORE_UPDATE, MatchScoreUpdate),
    (ClientPackets.MATCH_COMPLETE, MatchComplete),
    (ClientPackets.MATCH_CHANGE_MODS, MatchChangeMods),
    (ClientPackets.MATCH_LOAD_COMPLETE, MatchLoadComplete),
    (ClientPackets.MATCH_NO_BEATMAP, MatchNoBeatmap),
    (ClientPackets.MATCH_NOT_READY, MatchNotReady),
    (ClientPackets.MATCH_FAILED, MatchFailed),
    (ClientPackets.MATCH_HAS_BEATMAP, MatchHasBeatmap),
    (ClientPackets.MATCH_SKIP_REQUEST, MatchSkipRequest),
    (ClientPackets.MATCH_INVITE, MatchInvite),
    (ClientPackets.MATCH_TRANSFER_HOST, MatchTransferHost),
    (ClientPackets.MATCH_CHANGE_TEAM, MatchChangeTeam),
    (ClientPackets.MATCH_CHANGE_PASSWORD, MatchChangePassword),
    (ClientPackets.START_SPECTATING, StartSpectating),
    (ClientPackets.STOP_SPECTATING, StopSpectating),
    (ClientPackets.SPECTATE_FRAMES, SpectateFrames),
    (ClientPackets.CANT_SPECTATE, CantSpectate),
    (ClientPackets.TOURNAMENT_MATCH_INFO_REQUEST, TourneyMatchInfoRequest),
    (ClientPackets.TOURNAMENT_JOIN_MATCH_CHANNEL, TourneyMatchJoinChannel),
    (ClientPackets.TOURNAMENT_LEAVE_MATCH_CHANNEL, TourneyMatchLeaveChannel),
):
    app.state.packets["all"][packet] = handler

# restricted users only allowed these
for packet, handler in (
    (ClientPackets.LOGOUT, Logout),
    (ClientPackets.USER_STATS_REQUEST, StatsRequest),
    (ClientPackets.RECEIVE_UPDATES, ReceiveUpdates),
    (ClientPackets.CHANGE_ACTION, ChangeAction),
    (ClientPackets.CHANNEL_JOIN, ChannelJoin),
    (ClientPackets.CHANNEL_PART, ChannelPart),
):
    app.state.packets["restricted"][packet] = handler
