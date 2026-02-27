
from .common import parse_beatmap, pack_beatmap, round_half_up
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.database.repositories import wrapper
from app.common.database.repositories import *
from sqlalchemy.orm import Session
from datetime import timedelta

import hashlib
import app

@wrapper.session_wrapper
def fix_beatmap_lead_in(beatmapset: DBBeatmapset, minimum_leadin: int = 1500, session: Session = ...) -> list[DBBeatmap]:
    """Update the .osu files of a beatmapset to set a minimum audio lead-in time"""
    updated_beatmaps = list()

    for beatmap in beatmapset.beatmaps:
        beatmap_file = app.session.storage.get_beatmap(beatmap.id)

        if not beatmap_file:
            continue

        parsed_beatmap = parse_beatmap(beatmap_file, beatmap.id)

        if parsed_beatmap is None:
            continue

        current_leadin_value = int(parsed_beatmap.audio_lead_in.total_seconds() * 1000)

        if current_leadin_value >= minimum_leadin:
            continue

        parsed_beatmap.audio_lead_in = timedelta(milliseconds=minimum_leadin)

        # Get new file
        content = pack_beatmap(parsed_beatmap)
        content_hash = hashlib.md5(content).hexdigest()

        # Upload to storage & update database
        app.session.storage.upload_beatmap_file(beatmap.id, content)
        beatmaps.update(beatmap.id, {'md5': content_hash}, session)

        updated_beatmaps.append(beatmap)

    return updated_beatmaps
