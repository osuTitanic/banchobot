
from .common import parse_beatmap, pack_beatmap, round_half_up
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.database.repositories import wrapper
from app.common.database.repositories import *
from sqlalchemy.orm import Session

import hashlib
import app
import re

@wrapper.session_wrapper
def fix_beatmap_decimal_values(beatmapset: DBBeatmapset, session: Session = ...) -> list[DBBeatmap]:
    """Update the .osu files of a beatmapset to round OD/AR/HP/CS values"""
    updated_beatmaps = list()

    for beatmap in beatmapset.beatmaps:
        beatmap_file = app.session.storage.get_beatmap(beatmap.id)

        if not beatmap_file:
            continue

        parsed_beatmap = parse_beatmap(beatmap_file, beatmap.id)

        if parsed_beatmap is None:
            continue

        beatmap_updates = {}

        difficulty_attributes = {
            'overall_difficulty': 'od',
            'approach_rate': 'ar',
            'hp_drain_rate': 'hp',
            'circle_size': 'cs'
        }

        for attribute_name, short_key in difficulty_attributes.items():
            value = getattr(parsed_beatmap, attribute_name)

            if float(value).is_integer():
                continue

            rounded_value = round_half_up(value)

            # Update value
            beatmap_updates[short_key] = rounded_value
            setattr(parsed_beatmap, attribute_name, float(rounded_value))

        if not beatmap_updates:
            continue

        # Get new file
        content = pack_beatmap(parsed_beatmap)

        # Upload to storage
        app.session.storage.upload_beatmap_file(beatmap.id, content)

        # Update beatmap hash
        beatmap_hash = hashlib.md5(content).hexdigest()
        beatmap_updates['md5'] = beatmap_hash

        # Update database
        beatmaps.update(
            beatmap.id,
            beatmap_updates,
            session=session
        )

        updated_beatmaps.append(beatmap)

    return updated_beatmaps
