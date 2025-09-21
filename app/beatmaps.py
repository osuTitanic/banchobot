
from typing import Dict, Tuple, Union
from io import BytesIO

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
    stream = BytesIO()

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

def parse_number(value: str) -> int | float:
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
