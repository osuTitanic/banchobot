
from discord.ext.commands import Cog
from typing import Callable

from app.common.database.objects import DBUser
from app.common.database import users
from app import session

import asyncio
import app

class BaseCog(Cog):
    def __init__(self) -> None:
        self.bot = session.bot
        self.redis = session.redis_async
        self.logger = session.logger
        self.storage = session.storage
        self.database = session.database
        self.requests = session.requests

    @staticmethod
    async def run_async(func: Callable, *args):
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)

    async def resolve_user(self, discord_id: int) -> DBUser | None:
        return await self.run_async(users.fetch_by_discord_id, discord_id)
