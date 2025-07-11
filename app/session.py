
from .common.helpers.filter import ChatFilter
from .common.cache.events import EventQueue
from .common.database import Postgres
from .common.storage import Storage
from .manager import CommandManager

from requests import Session
from typing import Optional
from discord import Client
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

events = EventQueue(
    name='bancho:events',
    connection=redis
)

logger = logging.getLogger('banchobot')
bot: Optional[Client] = None

commands = CommandManager()
filters = ChatFilter()
storage = Storage()

requests = Session()
requests.headers = {
    'User-Agent': f'osuTitanic/banchobot ({config.DOMAIN_NAME})'
}
