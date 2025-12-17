
from app.common.config import config_instance as config
from app.common.database.objects import DBScore, DBUser
from app.common.database.repositories import scores
from app.common.constants import Mods, GameMode
from app.extensions.types import *
from discord.ext.commands import Bot
from discord.ext import commands
from discord import Color, Embed
from app.cog import BaseCog
from typing import List

class TopScores(BaseCog):
    @commands.hybrid_command("top", description="Display the top plays of you or another player", aliases=["scores", "best"])
    async def top_scores(
        self,
        ctx: commands.Context,
        username: str | None = None,
        mode: ModeType | None = None
    ) -> None:
        user = (
            await self.resolve_user(ctx.author.id) if username is None else
            await self.resolve_user_from_identifier(username)
        )

        if user is None:
            message = (
                "You don't have an account linked." if username is None else
                "No user found with that name."
            )
            return await ctx.send(
                message,
                ephemeral=True,
                reference=ctx.message
            )

        target_mode = user.preferred_mode

        if mode is not None:
            target_mode = Modes.get(mode, target_mode)

        user_scores = await self.fetch_top_scores(
            user.id,
            target_mode,
            limit=10
        )

        if not user_scores:
            message = (
                "You don't have any scores submitted yet. Go play some maps!" if username is None else
                "This user doesn't have any scores submitted yet."
            )
            return await ctx.send(
                message,
                ephemeral=True,
                reference=ctx.message
            )

        return await ctx.send(
            embed=self.render_embed(user_scores, user),
            reference=ctx.message
        )

    async def fetch_top_scores(self, user_id: int, mode: int, limit: int = 100) -> List[DBScore]:
        with self.database.managed_session() as session:
            user_scores = await self.run_async(
                scores.fetch_top_scores,
                user_id, mode, True,
                limit, 0, session
            )

            for score in user_scores:
                # Preload beatmap(set) relationships
                score.beatmap
                score.beatmap.beatmapset

            return user_scores
        
    def render_embed(self, user_scores: List[DBScore], user: DBUser) -> Embed:
        embed = Embed(
            title=f"Top plays for {user.name}",
            url=f"http://osu.{config.DOMAIN_NAME}/u/{user.id}#leader",
            color=Color.blue(),
            description=""
        )
        embed.set_thumbnail(url=f"http://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")

        for position, score in enumerate(user_scores, start=1):
            mods = Mods(score.mods)
            beatmap_title = f"{score.beatmap.full_name} +{mods}"
            embed.description += f"{position}. {beatmap_title}\n"
            embed.description += (
                f"   {score.grade} {score.max_combo}/{score.beatmap.max_combo} "
                f"{score.acc*100:.2f}% [{score.n300}/{score.n100}/{score.n50}/{score.nMiss}] "
                f"{score.pp:.2f}pp\n"
            )

        return embed

async def setup(bot: Bot):
    await bot.add_cog(TopScores())
