
from ossapi.ossapiv2_async import OssapiAsync
from discord.ext.commands import Cog
from typing import Callable

from app.common.database.objects import DBUser, DBBeatmapset
from app.common.config import config_instance as config
from app.common.helpers import permissions
from app.common.database import users
from app import session

import hashlib
import asyncio

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
        self.ossapi: OssapiAsync | None = None

        if not config.OSU_CLIENT_ID or not config.OSU_CLIENT_SECRET:
            return

        self.ossapi = OssapiAsync(
            config.OSU_CLIENT_ID,
            config.OSU_CLIENT_SECRET
        )

    @staticmethod
    async def run_async(func: Callable, *args, **kwargs):
        function_wrapper = lambda: func(*args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, function_wrapper)

    @staticmethod
    def avatar_url(user: DBUser) -> str:
        url = f"http://osu.{config.DOMAIN_NAME}/a/{user.id}"
        url += f"?c={user.avatar_hash}" if user.avatar_hash else ""
        return url

    @staticmethod
    def thumbnail_url(beatmapset: DBBeatmapset) -> str:
        update_hash = hashlib.md5(f'{beatmapset.last_update}'.encode()).hexdigest()
        url = f"http://osu.{config.DOMAIN_NAME}/mt/{beatmapset.id}"
        url += f"?c={update_hash}"
        return url

    async def resolve_user(self, discord_id: int) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_discord_id,
            discord_id
        )

    async def resolve_user_by_id(self, user_id: int) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_id,
            user_id
        )

    async def resolve_user_by_name(self, username: str) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_name_extended,
            username
        )

    async def resolve_user_by_name_case_insensitive(self, username: str) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_name_case_insensitive,
            username
        )
        
    async def resolve_user_by_safe_name(self, username: str) -> DBUser | None:
        return await self.run_async(
            users.fetch_by_safe_name,
            username
        )

    async def resolve_user_from_identifier(self, identifier: str) -> DBUser | None:
        identifier = identifier.strip()

        if identifier.isnumeric():
            return await self.resolve_user_by_id(int(identifier))

        if identifier.startswith("<@") and identifier.endswith(">"):
            discord_id = identifier[2:-1]
            discord_id = discord_id.strip("!")

            if discord_id.isnumeric():
                return await self.resolve_user(int(discord_id))

        return await self.resolve_user_by_name_case_insensitive(identifier)

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

    async def has_permission(self, user_id: int, permission: str) -> bool:
        return await self.run_async(
            permissions.has_permission,
            permission, user_id
        )
