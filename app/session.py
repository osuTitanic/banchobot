
from .common.helpers.filter import ChatFilter
from .common.cache.events import EventQueue
from .common.database import Postgres
from .common.storage import Storage

from redis.asyncio import Redis as RedisAsync
from discord.ext.commands import Bot
from requests import Session
from typing import Optional
from redis import Redis

import logging
import config

database = Postgres(
    config.POSTGRES_USER,
    config.POSTGRES_PASSWORD,
    config.POSTGRES_HOST,
    config.POSTGRES_PORT
)

redis = Redis(
    config.REDIS_HOST,
    config.REDIS_PORT
)

redis_async = RedisAsync(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT
)

events = EventQueue(
    name='bancho:events',
    connection=redis
)

logger = logging.getLogger('banchobot')
bot: Optional[Bot] = None

filters = ChatFilter()
storage = Storage()
requests = Session()
requests.headers = {
    'User-Agent': f'osuTitanic/banchobot ({config.DOMAIN_NAME})'
}
