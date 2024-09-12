
from app.common.database import DBBeatmap, DBBeatmapset
from app.common.database import beatmapsets, beatmaps
from typing import Dict, Union, List, Tuple
from ossapi import Beatmap

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

def get_beatmap_file(beatmap_dict: Dict[str, dict], format_version: int = 9) -> bytes:
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
                stream.write(f'{key}: {value}\r\n'.encode())

        else:
            # Write lines
            for value in items:
                stream.write(f'{value}\r\n'.encode())

        stream.write(b'\r\n')

    return stream.getvalue()

def add_beatmapset(set_id: int, maps: List[Beatmap]) -> DBBeatmapset:
    filesize = 0
    filesize_novideo = 0

    if (response := app.session.storage.api.osz(set_id, no_video=False)):
        filesize = int(response.headers.get('Content-Length', default=0))

    if maps[0].video and (response := app.session.storage.api.osz(set_id, no_video=True)):
        filesize_novideo = int(response.headers.get('Content-Length', default=0))

    with app.session.database.managed_session() as session:
        db_set = beatmapsets.create(
            maps[0].beatmapset_id,
            maps[0].title, maps[0].artist,
            maps[0].creator, maps[0].source,
            maps[0].tags, maps[0].approved,
            maps[0].video, maps[0].storyboard,
            maps[0].language_id, maps[0].genre_id,
            filesize, filesize_novideo,
            submit_date=maps[0].submit_date,
            approved_date=maps[0].approved_date,
            last_update=maps[0].last_update,
            session=session
        )

        for beatmap in maps:
            beatmaps.create(
                beatmap.beatmap_id, beatmap.beatmapset_id,
                beatmap.mode, beatmap.beatmap_hash,
                beatmap.approved, beatmap.version,
                get_beatmap_filename(beatmap.beatmap_id),
                beatmap.total_length, beatmap.max_combo,
                beatmap.bpm, beatmap.circle_size,
                beatmap.approach_rate, beatmap.overrall_difficulty,
                beatmap.health, beatmap.star_rating,
                beatmap.submit_date, beatmap.last_update,
                session=session
            )

        return db_set

def fix_beatmapset(beatmapset: DBBeatmapset) -> List[DBBeatmap]:
    updated_beatmaps = list()

    for beatmap in beatmapset.beatmaps:
        beatmap_file = app.session.storage.get_beatmap(beatmap.id).decode()
        version, beatmap_dict = parse_beatmap_file(beatmap_file)
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
        beatmaps.update(beatmap.id, beatmap_updates)

        updated_beatmaps.append(beatmap)

    return updated_beatmaps
