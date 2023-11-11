
from app.common.database import DBScore
from datetime import datetime

import requests
import hashlib
import config
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
