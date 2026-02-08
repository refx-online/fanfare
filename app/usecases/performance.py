from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import replace
from typing import Any

import app
from app.adapters.omajinai import PerformanceResult


@dataclass
class ScoreParams:
    mode: int
    mods: int | None = None
    combo: int | None = None
    acc: float | None = None
    nmiss: int | None = None
    legacy_score: int | None = None


async def calculate_performances(
    beatmap_id: int,
    scores: Iterable[ScoreParams],
) -> list[dict[str, Any]]:
    """\
    Calculate performance for multiple scores on a single beatmap.

    Typically most useful for mass-recalculation situations.
    """

    async def _(score: ScoreParams) -> dict[str, Any]:
        # HACK: handling !with command
        if not score.acc:
            score.acc = 100.0

        result: PerformanceResult = (
            await app.state.services.omajinai.calculate_performance_single(
                beatmap_id=beatmap_id,
                mode=score.mode,
                mods=score.mods,
                max_combo=score.combo,
                accuracy=score.acc,
                miss_count=score.nmiss,
                legacy_score=score.legacy_score,
            )
        )

        return {
            "performance": {"pp": result.pp, "hypothetical_pp": result.hypothetical_pp},
            "difficulty": {"stars": result.stars},
        }

    # parallelize calculations
    # each calculation is independent of the others
    # and the performance gain is *GODLY*
    return await asyncio.gather(*[_(score) for score in scores])


def calculate_accuracy(
    mode_vn: int,
    n300: int,
    n100: int,
    n50: int,
    nmiss: int,
    nkatu: int,
    ngeki: int,
    score_v2: bool,
) -> float:
    """Used for pp competition matches to calculate accuracy."""

    if mode_vn == 0:  # osu!std
        total = n300 + n100 + n50 + nmiss
        if total == 0:
            return 0.0
        return (
            100.0 * ((n300 * 300.0) + (n100 * 100.0) + (n50 * 50.0)) / (total * 300.0)
        )

    elif mode_vn == 1:  # osu!taiko
        total = n300 + n100 + nmiss
        if total == 0:
            return 0.0
        return 100.0 * ((n100 * 0.5) + n300) / total

    elif mode_vn == 2:  # osu!catch
        total = n300 + n100 + n50 + nkatu + nmiss
        if total == 0:
            return 0.0
        return 100.0 * (n300 + n100 + n50) / total

    elif mode_vn == 3:  # osu!mania
        total = n300 + n100 + n50 + ngeki + nkatu + nmiss
        if total == 0:
            return 0.0

        if score_v2:
            return (
                100.0
                * (
                    (n50 * 50.0)
                    + (n100 * 100.0)
                    + (nkatu * 200.0)
                    + (n300 * 300.0)
                    + (ngeki * 305.0)
                )
                / (total * 305.0)
            )

        return (
            100.0
            * (
                (n50 * 50.0)
                + (n100 * 100.0)
                + (nkatu * 200.0)
                + ((n300 + ngeki) * 300.0)
            )
            / (total * 300.0)
        )

    else:
        raise ValueError(f"invalid vanilla mode {mode_vn}")
