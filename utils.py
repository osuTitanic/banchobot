
from app.common.database.repositories.wrapper import session_wrapper
from app.common.database import DBBeatmap, DBBeatmapset
from app.common.database import beatmapsets, beatmaps
from typing import Dict, Union, List, Tuple
from sqlalchemy.orm import Session
from ossapi import Beatmapset

import hashlib
import config
import app
import io
import re
import os

def setup() -> None:
    if config.S3_ENABLED:
        return

    # Create required folders if not they not already exist
    os.makedirs(f'{config.DATA_PATH}/images/achievements', exist_ok=True)
    os.makedirs(f'{config.DATA_PATH}/screenshots', exist_ok=True)
    os.makedirs(f'{config.DATA_PATH}/beatmaps', exist_ok=True)
    os.makedirs(f'{config.DATA_PATH}/replays', exist_ok=True)
    os.makedirs(f'{config.DATA_PATH}/avatars', exist_ok=True)

def sanitize_response(message: str) -> str:
    return message.replace('@', '@\u200b')

def get_beatmap_filename(id: int) -> str:
    response = app.session.requests.head(f'https://old.ppy.sh/osu/{id}')

    if not response.ok:
        return ''

    if not (cd := response.headers.get('content-disposition')):
        return ''

    return re.findall("filename=(.+)", cd)[0] \
             .removeprefix('"') \
             .removesuffix('"')

def parse_beatmap_file(content: str) -> Tuple[int, Dict[str, dict]]:
    """Parse a beatmap file into a list"""
    sections: Dict[str, Union[dict, list]] = {}
    current_section = None
    beatmap_version = 0

    for line in content.splitlines():
        if line.startswith('osu file format'):
            beatmap_version = int(line.removeprefix('osu file format v'))
            continue

        if (line.startswith('[') and line.endswith(']')):
            # New section
            current_section = line.removeprefix('[').removesuffix(']')
            continue

        if current_section is None:
            continue

        if not line:
            continue

        if current_section in ('General', 'Editor', 'Metadata', 'Difficulty'):
            if current_section not in sections:
                sections[current_section] = {}

            # Parse key, value pair
            key, value = (
                split.strip() for split in line.split(':', maxsplit=1)
            )

            # Parse float/int
            if value.isdigit(): value = int(value)
            elif value.replace('.', '').isnumeric(): value = float(value)

            sections[current_section][key] = value
            continue

        if current_section not in sections:
            sections[current_section] = []

        # Append to list
        sections[current_section].append(line)

    return beatmap_version, sections

def get_beatmap_file(beatmap_dict: Dict[str, dict], format_version: int) -> bytes:
    """Create a beatmap file from a beatmap dictionary"""
    stream = io.BytesIO()

    # Write format version
    stream.write(
        f'osu file format v{format_version}\r\n\r\n'.encode()
    )

    for section, items in beatmap_dict.items():
        stream.write(f'[{section}]\r\n'.encode())

        if isinstance(items, dict):
            # Write key, value pairs
            for key, value in items.items():
                stream.write(
                    f'{key}: {value}\r\n'.encode()
                    if section not in ('Metadata', 'Difficulty')
                    else f'{key}:{value}\r\n'.encode()
                )

        else:
            # Write lines
            for value in items:
                stream.write(f'{value}\r\n'.encode())

        stream.write(b'\r\n')

    return stream.getvalue().removesuffix(b'\r\n')

@session_wrapper
def add_beatmapset(
    set_id: int,
    set: Beatmapset,
    session: Session = ...
) -> DBBeatmapset:
    filesize = 0
    filesize_novideo = 0

    if (response := app.session.storage.api.osz(set_id, no_video=False)):
        filesize = int(response.headers.get('Content-Length', default=0))

    if set.video and (response := app.session.storage.api.osz(set_id, no_video=True)):
        filesize_novideo = int(response.headers.get('Content-Length', default=0))

    db_set = beatmapsets.create(
        set.id,
        set.title, set.title_unicode,
        set.artist, set.artist_unicode,
        set.creator, set.source,
        set.tags, set.description['description'],
        set.status.value,
        set.video, set.storyboard,
        set.language['id'], set.genre['id'],
        filesize, filesize_novideo,
        available=(not set.availability.download_disabled),
        submit_date=set.submitted_date,
        approved_date=set.ranked_date,
        last_update=set.last_updated,
        session=session
    )

    for beatmap in set.beatmaps:
        beatmaps.create(
            beatmap.id, beatmap.beatmapset_id,
            beatmap.mode_int, beatmap.checksum,
            beatmap.status.value, beatmap.version,
            get_beatmap_filename(beatmap.id),
            beatmap.total_length, beatmap.max_combo,
            beatmap.bpm, beatmap.cs,
            beatmap.ar, beatmap.accuracy,
            beatmap.drain, beatmap.difficulty_rating,
            set.submitted_date, beatmap.last_updated,
            session=session
        )

    return db_set

@session_wrapper
def fix_beatmapset(beatmapset: DBBeatmapset, session: Session = ...) -> List[DBBeatmap]:
    updated_beatmaps = list()

    for beatmap in beatmapset.beatmaps:
        beatmap_file = app.session.storage.get_beatmap(beatmap.id)

        if not beatmap_file:
            continue

        version, beatmap_dict = parse_beatmap_file(beatmap_file.decode())
        beatmap_updates = {}

        difficulty_attributes = {
            'OverallDifficulty': 'od',
            'ApproachRate': 'ar',
            'HPDrainRate': 'hp',
            'CircleSize': 'cs'
        }

        for key, short_key in difficulty_attributes.items():
            if key not in beatmap_dict['Difficulty']:
                continue

            value = beatmap_dict['Difficulty'][key]

            if isinstance(value, int):
                continue

            # Update value
            beatmap_updates[short_key] = round(value) # Database
            beatmap_dict['Difficulty'][key] = round(value) # File

        if not beatmap_updates:
            continue

        # Get new file
        content = get_beatmap_file(beatmap_dict, version)

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
