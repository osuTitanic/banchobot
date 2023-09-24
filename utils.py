
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

def compute_score_checksum(score: DBScore) -> str:
    return hashlib.md5(
        '{}p{}o{}o{}t{}a{}r{}e{}y{}o{}u{}{}{}'.format(
            (score.n100 + score.n300),
            score.n50,
            score.nGeki,
            score.nKatu,
            score.nMiss,
            score.beatmap.md5,
            score.max_combo,
            score.perfect,
            score.user.name,
            score.total_score,
            score.grade,
            score.mods,
            (not score.failtime) # (passed)
        ).encode()
    ).hexdigest()

def get_ticks(dt) -> int:
    dt = dt.replace(tzinfo=None)
    return int((dt - datetime(1, 1, 1)).total_seconds() * 10000000)

def get_beatmap_filename(id: int) -> str:
    response = requests.head(f'https://old.ppy.sh/osu/{id}')

    if not response.ok:
        return ''

    if not (cd := response.headers.get('content-disposition')):
        return ''

    return re.findall("filename=(.+)", cd)[0] \
            .removeprefix('"') \
            .removesuffix('"')
