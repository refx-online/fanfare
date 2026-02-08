"""bmap: static beatmap info (thumbnails, previews, etc.)"""

from __future__ import annotations

from pathlib import Path as SystemPath

from fastapi import APIRouter
from fastapi import Response
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse
from fastapi.responses import RedirectResponse

from app.objects.beatmap import Beatmap
from app.objects.beatmap import ensure_osu_file_is_available

BEATMAPS_PATH = SystemPath.cwd() / ".data/osu"
# import app.settings

router = APIRouter(tags=["Beatmaps"])


# /v1 Because forlorn and im not compiling again
@router.get("/v1/get-osu/{beatmap_id}")
async def get_osu_file(
    beatmap_id: int,
) -> Response:
    """Returns beatmap bytes from given beatmap id"""
    beatmap = await Beatmap.from_bid(beatmap_id)
    if not beatmap:
        return ORJSONResponse(
            {"status": "Beatmap not found."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    osu_file_available = await ensure_osu_file_is_available(
        beatmap.id,
        expected_md5=beatmap.md5,
    )
    if not osu_file_available:
        return ORJSONResponse(
            {"status": "Beatmap file could not be fetched."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    map_path = BEATMAPS_PATH / f"{beatmap.id}.osu"

    try:
        file_bytes = map_path.read_bytes()
    except FileNotFoundError:
        return ORJSONResponse(
            {"status": "Beatmap file not found on disk."},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        content=file_bytes,
        media_type="application/octet-stream",
        headers={"Content-Description": "File Transfer"},
    )


# forward any unmatched request to osu!
# eventually if we do bmap submission, we'll need this.
@router.get("/{file_path:path}")
async def everything(request: Request) -> RedirectResponse:
    return RedirectResponse(
        url=f"https://b.ppy.sh{request['path']}",
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )
