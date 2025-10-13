
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.database.repositories import wrapper
from app.common.database.repositories import *
from typing import Dict, Tuple, Union, List
from sqlalchemy.orm import Session
from ossapi import Beatmapset

import hashlib
import app
import re
import io

def deserialize(content: str) -> Tuple[int, Dict[str, dict]]:
    """Parse a beatmap file into a dictionary"""
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

            # Try to parse float/int
            value = parse_number(value) or value

            sections[current_section][key] = value
            continue

        if current_section not in sections:
            sections[current_section] = []

        # Append to list
        sections[current_section].append(line)

    return beatmap_version, sections

def serialize(beatmap_dict: Dict[str, dict], osu_file_version: int) -> bytes:
    """Create a beatmap file from a beatmap dictionary"""
    stream = io.BytesIO()

    # Write beatmap file version
    stream.write(
        f'osu file format v{osu_file_version}\r\n\r\n'.encode()
    )

    # Write individual sections
    for section, items in beatmap_dict.items():
        stream.write(serialize_section(section, items))

    return stream.getvalue().removesuffix(b'\r\n')

def serialize_section(section: str, items: dict | list) -> bytes:
    result = f'[{section}]\r\n'.encode()

    if isinstance(items, dict):
        # Write key, value pairs
        for key, value in items.items():
            result += (
                f'{key}: {value}\r\n'.encode()
                if section not in ('Metadata', 'Difficulty')
                else f'{key}:{value}\r\n'.encode()
            )

    else:
        # Write lines
        for value in items:
            result += (f'{value}\r\n'.encode())

    result += b'\r\n'
    return result

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

@wrapper.session_wrapper
def fix_beatmap_files(beatmapset: DBBeatmapset, session: Session = ...) -> List[DBBeatmap]:
    """Update the .osu files of a beatmapset to round OD/AR/HP/CS values"""
    updated_beatmaps = list()

    for beatmap in beatmapset.beatmaps:
        beatmap_file = app.session.storage.get_beatmap(beatmap.id)

        if not beatmap_file:
            continue

        version, beatmap_dict = deserialize(beatmap_file.decode())
        beatmap_updates = {}
        
        if 'Difficulty' not in beatmap_dict:
            # Invalid beatmap file somehow...
            app.session.logger.warning(f"Invalid beatmap file for '{beatmap.id}'")
            continue

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
        content = serialize(beatmap_dict, version)

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

@wrapper.session_wrapper
def delete_beatmapset(beatmapset: DBBeatmapset, session: Session = ...) -> None:
    app.session.storage.remove_osz2(beatmapset.id)
    app.session.storage.remove_osz(beatmapset.id)
    app.session.storage.remove_background(beatmapset.id)
    app.session.storage.remove_mp3(beatmapset.id)

    for beatmap in beatmapset.beatmaps:
        app.session.storage.remove_beatmap_file(beatmap.id)
    
    # Delete all related data
    for beatmap in beatmapset.beatmaps:
        collaborations.delete_requests_by_beatmap(beatmap.id, session=session)
        collaborations.delete_by_beatmap(beatmap.id, session=session)

    modding.delete_by_set_id(beatmapset.id, session=session)
    ratings.delete_by_set_id(beatmapset.id, session=session)
    plays.delete_by_set_id(beatmapset.id, session=session)
    nominations.delete_all(beatmapset.id, session=session)
    favourites.delete_all(beatmapset.id, session=session)
    beatmaps.delete_by_set_id(beatmapset.id, session=session)
    beatmapsets.delete_by_id(beatmapset.id, session=session)

@wrapper.session_wrapper
def delete_beatmap(beatmap: DBBeatmap, session: Session = ...) -> None:
    app.session.storage.remove_beatmap_file(beatmap.id)

    collaborations.delete_requests_by_beatmap(beatmap.id, session=session)
    collaborations.delete_by_beatmap(beatmap.id, session=session)
    ratings.delete_by_beatmap_hash(beatmap.md5, session=session)
    plays.delete_by_beatmap_id(beatmap.id, session=session)
    beatmaps.delete_by_id(beatmap.id, session=session)

def parse_number(value: str) -> int | float:
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
