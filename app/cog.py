
from discord.ext.commands import Cog
from config import DOMAIN_NAME
from typing import Callable

from app.common.database.objects import DBUser, DBBeatmapset
from app.common.database import users
from app import session

import hashlib
import asyncio
import app

class BaseCog(Cog):
    def __init__(self) -> None:
        self.bot = session.bot
        self.guild = session.bot.guilds[0]
        self.redis = session.redis_async
        self.logger = session.logger
        self.events = session.events
        self.storage = session.storage
        self.filters = session.filters
        self.database = session.database
        self.requests = session.requests

    @staticmethod
    async def run_async(func: Callable, *args):
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)

    @staticmethod
    def avatar_url(user: DBUser) -> str:
        url = f"http://osu.{DOMAIN_NAME}/a/{user.id}"
        url += f"?c={user.avatar_hash}" if user.avatar_hash else ""
        return url

    @staticmethod
    def thumbnail_url(beatmapset: DBBeatmapset) -> str:
        update_hash = hashlib.md5(f'{beatmapset.last_update}'.encode()).hexdigest()
        url = f"http://osu.{DOMAIN_NAME}/mt/{beatmapset.id}"
        url += f"?c={update_hash}"
        return url

    async def resolve_user(self, discord_id: int) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_discord_id,
            discord_id
        )

    async def resolve_user_by_name(self, username: str) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_name_extended,
            username
        )

    async def update_user(self, user_id: int, updates: dict) -> int:
        return await self.run_async(
            users.update,
            user_id, updates
        )

    async def submit_event(self, name: str, *args) -> None:
        return await self.run_async(
            self.events.submit,
            name, *args
        )
