
from app.common.config import config_instance as config
from app.common.database.objects import DBUser, DBStats
from app.common.database.repositories import users
from app.common.cache import leaderboards
from app.extensions.types import *
from discord.ext.commands import Bot
from discord import Embed, Color
from discord.ext import commands
from app.cog import BaseCog

class Profile(BaseCog):
    @commands.hybrid_command("profile", description="Display the profile of you or another person", aliases=["stats", "show"])
    async def profile(
        self,
        ctx: commands.Context,
        username: str | None = None,
        mode: ModeType | None = None
    ) -> None:
        if not (user := await self.resolve_user_with_stats(ctx.author.id, username)):
            message = (
                "You don't have an account linked." if username is None else
                "No user found with that name."
            )
            return await ctx.send(
                message,
                ephemeral=True,
                reference=ctx.message
            )

        if not user.stats:
            message = (
                "You have not played the game yet." if username is None else
                "No statistics for this user found."
            )
            return await ctx.send(
                message,
                ephemeral=True,
                reference=ctx.message
            )

        target_mode = user.preferred_mode

        if mode is not None:
            target_mode = Modes.get(mode, target_mode)

        rankings = await self.player_rankings(
            user.id, target_mode, user.country,
            ("performance", "ppv1", "rscore", "tscore")
        )
        stats: DBStats = user.stats[target_mode]

        return await ctx.send(
            embed=self.render_embed(user, stats, rankings),
            reference=ctx.message
        )

    async def player_rankings(
        self,
        user_id: int,
        mode: int,
        country: str,
        rankings = (
            "performance", "ppv1",
            "rscore", "tscore",
        )
    ) -> dict:
        return await self.run_async(
            leaderboards.player_rankings,
            user_id, mode, country, rankings
        )

    async def resolve_user_with_stats(self, author_id: int, username: str | None = None) -> DBUser | None:
        with self.database.managed_session() as session:
            if username is None:
                user = await self.run_async(
                    users.fetch_by_discord_id,
                    author_id, session
                )

            else:
                user = await self.run_async(
                    users.fetch_by_name_extended,
                    username, session
                )

            if not user:
                return None

            # Preload relationships & sort stats
            user.stats.sort(key=lambda s: s.mode)
            return user

    def render_embed(self, user: DBUser, stats: DBStats, rankings: dict) -> Embed:
        embed = Embed(
            title=f"Statistics for {user.name}",
            url=f"http://osu.{config.DOMAIN_NAME}/u/{user.id}",
            color=Color.blue(),
        )
        embed.add_field(
            name="Ranked score", 
            value=f"{stats.rscore:,} (#{rankings['rscore']['global']})"
        )
        embed.add_field(
            name="Total score", 
            value=f"{stats.tscore:,} (#{rankings['tscore']['global']})"
        )
        embed.add_field(
            name="Total hits", 
            value=f"{stats.total_hits:,}"
        )
        embed.add_field(
            name="Play count", 
            value=f"{stats.playcount:,}"
        )
        embed.add_field(
            name="Play time", 
            value=f"{stats.playtime/60/60:,.2f}h"
        )
        embed.add_field(
            name="Replay views",
            value=f"{stats.replay_views:,}"
        )
        embed.add_field(
            name="Accuracy",
            value=f"{stats.acc*100:.2f}%"
        )
        embed.add_field(
            name="Max combo",
            value=f"{stats.max_combo:,}"
        )
        embed.add_field(
            name="Performance points",
            value=f"{stats.pp:.0f}pp, {stats.ppv1:.0f}ppv1 (#{rankings['performance']['global']}, #{rankings['ppv1']['global']})"
        )
        embed.add_field(
            name="SS/SS+",
            value=f"{stats.x_count}/{stats.xh_count}"
        )
        embed.add_field(
            name="S/S+",
            value=f"{stats.s_count}/{stats.sh_count}"
        )
        embed.add_field(
            name="A/B/C/D",
            value=f"{stats.a_count}/{stats.b_count}/{stats.c_count}/{stats.d_count}",
        )
        embed.set_thumbnail(url=f"http://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
        return embed

async def setup(bot: Bot):
    await bot.add_cog(Profile())
