from __future__ import annotations

import functools
from datetime import datetime
from enum import IntEnum
from enum import unique
from pathlib import Path
from typing import TYPE_CHECKING

import app.state
from app.constants.clientflags import ClientFlags
from app.constants.gamemodes import GameMode
from app.constants.mods import Mods
from app.objects.beatmap import Beatmap
from app.repositories import scores as scores_repo
from app.utils import escape_enum
from app.utils import pymysql_encode

if TYPE_CHECKING:
    from app.objects.player import Player

BEATMAPS_PATH = Path.cwd() / ".data/osu"


@unique
class Grade(IntEnum):
    # NOTE: these are implemented in the opposite order
    # as osu! to make more sense with <> operators.
    N = 0
    F = 1
    D = 2
    C = 3
    B = 4
    A = 5
    S = 6  # S
    SH = 7  # HD S
    X = 8  # SS
    XH = 9  # HD SS

    @classmethod
    @functools.cache
    def from_str(cls, s: str) -> Grade:
        return {
            "xh": Grade.XH,
            "x": Grade.X,
            "sh": Grade.SH,
            "s": Grade.S,
            "a": Grade.A,
            "b": Grade.B,
            "c": Grade.C,
            "d": Grade.D,
            "f": Grade.F,
            "n": Grade.N,
        }[s.lower()]

    def __format__(self, format_spec: str) -> str:
        if format_spec == "stats_column":
            return f"{self.name.lower()}_count"
        else:
            raise ValueError(f"Invalid format specifier {format_spec}")


@unique
@pymysql_encode(escape_enum)
class SubmissionStatus(IntEnum):
    # TODO: make a system more like bancho's?
    FAILED = 0
    SUBMITTED = 1
    BEST = 2

    def __repr__(self) -> str:
        return {
            self.FAILED: "Failed",
            self.SUBMITTED: "Submitted",
            self.BEST: "Best",
        }[self]


class Score:
    """\
    Server side representation of an osu! score; any gamemode.

    Possibly confusing attributes
    -----------
    bmap: `Beatmap | None`
        A beatmap obj representing the osu map.

    player: `Player | None`
        A player obj of the player who submitted the score.

    grade: `Grade`
        The letter grade in the score.

    rank: `int`
        The leaderboard placement of the score.

    perfect: `bool`
        Whether the score is a full-combo.

    time_elapsed: `int`
        The total elapsed time of the play (in milliseconds).

    client_flags: `int`
        osu!'s old anticheat flags.

    prev_best: `Score | None`
        The previous best score before this play was submitted.
        NOTE: just because a score has a `prev_best` attribute does
        mean the score is our best score on the map! the `status`
        value will always be accurate for any score.
    """

    def __init__(self) -> None:
        # TODO: check whether the reamining Optional's should be
        self.id: int | None = None
        self.bmap: Beatmap | None = None
        self.player: Player | None = None

        self.mode: GameMode
        self.mods: Mods

        self.pp: float
        self.sr: float
        self.score: int
        self.max_combo: int
        self.acc: float

        # TODO: perhaps abstract these differently
        # since they're mode dependant? feels weird..
        self.n300: int
        self.n100: int  # n150 for taiko
        self.n50: int
        self.nmiss: int
        self.ngeki: int
        self.nkatu: int

        self.grade: Grade

        self.passed: bool
        self.perfect: bool
        self.status: SubmissionStatus

        self.client_time: datetime
        self.server_time: datetime
        self.time_elapsed: int

        self.client_flags: ClientFlags
        self.client_checksum: str

        self.rank: int | None = None
        self.prev_best: Score | None = None

    def __repr__(self) -> str:
        # TODO: i really need to clean up my reprs
        try:
            assert self.bmap is not None
            return (
                f"<{self.acc:.2f}% {self.max_combo}x {self.nmiss}M "
                f"#{self.rank} on {self.bmap.full_name} for {self.pp:,.2f}pp>"
            )
        except:
            return super().__repr__()

    """Classmethods to fetch a score object from various data types."""

    @classmethod
    async def from_sql(cls, score_id: int) -> Score | None:
        """Create a score object from sql using its scoreid."""
        rec = await scores_repo.fetch_one(score_id)

        if rec is None:
            return None

        s = cls()

        s.id = rec["id"]
        s.bmap = await Beatmap.from_md5(rec["map_md5"])
        s.player = await app.state.sessions.players.from_cache_or_sql(id=rec["userid"])

        s.sr = 0.0  # TODO

        s.pp = rec["pp"]
        s.score = rec["score"]
        s.max_combo = rec["max_combo"]
        s.mods = Mods(rec["mods"])
        s.acc = rec["acc"]
        s.n300 = rec["n300"]
        s.n100 = rec["n100"]
        s.n50 = rec["n50"]
        s.nmiss = rec["nmiss"]
        s.ngeki = rec["ngeki"]
        s.nkatu = rec["nkatu"]
        s.grade = Grade.from_str(rec["grade"])
        s.perfect = rec["perfect"] == 1
        s.status = SubmissionStatus(rec["status"])
        s.passed = s.status != SubmissionStatus.FAILED
        s.mode = GameMode(rec["mode"])
        s.server_time = rec["play_time"]
        s.time_elapsed = rec["time_elapsed"]
        s.client_flags = ClientFlags(rec["client_flags"])
        s.client_checksum = rec["online_checksum"]

        if s.bmap:
            s.rank = await s.calculate_placement()

        return s

    """Methods to calculate internal data for a score."""

    async def calculate_placement(self) -> int:
        assert self.bmap is not None

        if self.mode >= GameMode.RELAX_OSU:
            scoring_metric = "pp"
            score = self.pp
        else:
            scoring_metric = "score"
            score = self.score

        num_better_scores: int | None = await app.state.services.database.fetch_val(
            "SELECT COUNT(*) AS c FROM scores s "
            "INNER JOIN users u ON u.id = s.userid "
            "WHERE s.map_md5 = :map_md5 AND s.mode = :mode "
            "AND s.status = 2 AND u.priv & 1 "
            f"AND s.{scoring_metric} > :score",
            {
                "map_md5": self.bmap.md5,
                "mode": self.mode,
                "score": score,
            },
            column=0,  # COUNT(*)
        )
        assert num_better_scores is not None
        return num_better_scores + 1

    """ Methods for updating a score. """
