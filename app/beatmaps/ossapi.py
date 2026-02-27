
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.database.repositories import wrapper
from app.common.database.repositories import *
from sqlalchemy.orm import Session
from ossapi import Beatmapset
from typing import Tuple

import hashlib
import app
import re

@wrapper.session_wrapper
def store_ossapi_beatmapset(set: Beatmapset, session: Session = ...) -> DBBeatmapset:
    """Convert an osu! api beatmapset to a local beatmapset and store it in the database"""
    database_set = beatmapsets.create(
        set.id,
        set.title, set.title_unicode,
        set.artist, set.artist_unicode,
        set.creator, set.source,
        set.tags, set.description['description'],
        set.status.value,
        set.video, set.storyboard,
        set.language['id'], set.genre['id'],
        osz_filesize=0,
        osz_filesize_novideo=0,
        available=(not set.availability.download_disabled),
        submit_date=set.submitted_date,
        approved_date=set.ranked_date,
        last_update=set.last_updated,
        session=session
    )

    for beatmap in set.beatmaps:
        beatmap = beatmaps.create(
            beatmap.id, beatmap.beatmapset_id,
            beatmap.mode_int, beatmap.checksum,
            beatmap.status.value, beatmap.version,
            resolve_beatmap_filename(beatmap.id),
            beatmap.total_length, beatmap.max_combo,
            beatmap.bpm, beatmap.cs,
            beatmap.ar, beatmap.accuracy,
            beatmap.drain, beatmap.difficulty_rating,
            set.submitted_date, beatmap.last_updated,
            session=session
        )
        database_set.beatmaps.append(beatmap)

    return database_set

def resolve_beatmap_filename(id: int) -> str:
    """Fetch the filename of a beatmap"""
    response = app.session.requests.head(f'https://osu.ppy.sh/osu/{id}')
    response.raise_for_status()

    if not (cd := response.headers.get('content-disposition')):
        raise ValueError('No content-disposition header found')

    return re.findall("filename=(.+)", cd)[0].strip('"')

def fetch_osz_filesizes(set_id: int) -> Tuple[int, int]:
    """Fetch the filesize of a beatmapset's .osz file from a mirror"""
    filesize, filesize_novideo = 0, 0

    if (response := app.session.storage.api.osz(set_id, no_video=False)):
        filesize = int(response.headers.get('Content-Length', default=0))

    if (response := app.session.storage.api.osz(set_id, no_video=True)):
        filesize_novideo = int(response.headers.get('Content-Length', default=0))

    return filesize, filesize_novideo
