
from app.common.config import config_instance as config
from app.common.database.repositories import users
from app.common.database.objects import DBUser
from app.common.cache import leaderboards
from app.common.constants import GameMode
from app.extensions.types import *
from discord.ext.commands import Bot
from discord.ext import commands
from discord import Embed, Color
from typing import Tuple, List
from app.cog import BaseCog

class Rankings(BaseCog):
    @commands.hybrid_command("rankings", description="Display rankings", aliases=["leaderboard", "lb"])
    async def rankings(
        self,
        ctx: commands.Context,
        mode: ModeType | None = "standard",
        type: RankingType | None = "performance"
    ) -> None:
        target_mode = Modes.get(mode, 0)
        mode_type = GameMode(target_mode)

        leaderboard = await self.fetch_top_players(target_mode, type)
        user_list = await self.fetch_many_users([user_id for user_id, _ in leaderboard])
        user_map = {user.id: user for user in user_list}

        response = ""
        extension = "pp" if type in ("performance", "ppv1") else " score"

        for rank, (user_id, value) in enumerate(leaderboard, start=1):
            user = user_map.get(user_id)
            response += (
                f"**#{rank} {user.name}** - {round(value)}{extension}\n" if user is not None else
                f"**#{rank} Unknown User (ID: {user_id})** - {round(value)}{extension}\n"
            )

        embed = Embed(
            title=f"{type.capitalize()} Rankings for {mode_type.formatted}",
            url=f"http://osu.{config.DOMAIN_NAME}/rankings/{type}/{mode_type.alias}",
            description=response,
            color=Color.blue()
        )

        return await ctx.send(
            embed=embed,
            reference=ctx.message
        )

    async def fetch_top_players(
        self,
        mode: int,
        type: str,
        offset: int = 0,
        range: int = 10,
        country: str | None = None
    ) -> List[Tuple[int, float]]:
        return await self.run_async(
            leaderboards.top_players,
            mode, offset, range, type, country
        )
        
    async def fetch_many_users(
        self,
        user_ids: List[int],
        *options
    ) -> List[DBUser]:
        return await self.run_async(
            users.fetch_many,
            user_ids, *options
        )

async def setup(bot: Bot):
    await bot.add_cog(Rankings())
