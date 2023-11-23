
from typing import Dict, Union

import requests
import config
import io
import re
import os

def setup():
    if not config.S3_ENABLED:
        # Create required folders if not they not already exist
        os.makedirs(f'{config.DATA_PATH}/images/achievements', exist_ok=True)
        os.makedirs(f'{config.DATA_PATH}/screenshots', exist_ok=True)
        os.makedirs(f'{config.DATA_PATH}/replays', exist_ok=True)
        os.makedirs(f'{config.DATA_PATH}/avatars', exist_ok=True)

def get_beatmap_filename(id: int) -> str:
    response = requests.head(f'https://old.ppy.sh/osu/{id}')

    if not response.ok:
        return ''

    if not (cd := response.headers.get('content-disposition')):
        return ''

    return re.findall("filename=(.+)", cd)[0] \
            .removeprefix('"') \
            .removesuffix('"')

def parse_beatmap_file(content: str) -> Dict[str, dict]:
    """Parse a beatmap file into a list"""
    sections: Dict[str, Union[dict, list]] = {}
    current_section = None

    for line in content.splitlines():
        line = line.strip()

        if (line.startswith('[') and line.endswith(']')):
            # New section
            current_section = line.removeprefix('[').removesuffix(']')
            continue

        if current_section is None:
            continue

        if not line:
            continue

        # if line.startswith('//'):
        #     continue

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

    return sections

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

    return stream.getvalue()
