
from rosu_pp_py import DifficultyAttributes
from app.common.database.objects import DBScore, DBUser
from app.common.database.repositories import scores
from app.common.constants import Mods, GameMode
from app.common.helpers import performance
from discord.ext.commands import Bot
from discord.ext import commands
from discord import Color, Embed
from app.cog import BaseCog
from typing import List

import config
import app

class RecentScore(BaseCog):
    @commands.hybrid_command("recent", description="Display the last score of another player or yourself", aliases=["r", "rs", "last"])
    async def recent_score(self, ctx: commands.Context, username: str | None = None) -> None:
        user = (
            await self.resolve_user(ctx.author.id) if username is None else
            await self.resolve_user_by_name(username)
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

        if not (score_list := await self.fetch_recent_scores(user.id, limit=1)):
            return await ctx.send(
                "No recent scores found.",
                reference=ctx.message,
                ephemeral=True
            )

        return await ctx.send(
            embed=await self.render_embed(score_list[0], user),
            reference=ctx.message
        )

    async def calculate_difficulty(
        self,
        beatmap_file: bytes,
        mode: int,
        mods: Mods = Mods.NoMod
    ) -> DifficultyAttributes | None:
        return await self.run_async(
            performance.calculate_difficulty,
            beatmap_file, mode, mods
        )
        
    async def calculate_fc_pp(
        self,
        score: DBScore
    ) -> float | None:
        return await self.run_async(
            performance.calculate_ppv2_if_fc,
            score
        )

    async def fetch_recent_scores(self, user_id: int, limit: int = 3) -> List[DBScore]:
        with self.database.managed_session() as session:
            response = await self.run_async(
                scores.fetch_recent_all,
                user_id, limit, session
            )

            for score in response:
                # Preload beatmap(set) relationship
                score.beatmap
                score.beatmap.beatmapset

            return response

    async def render_embed(self, score: DBScore, user: DBUser) -> Embed:
        beatmap_file = self.storage.get_beatmap(score.beatmap_id)
        mode = GameMode(score.mode)
        mods = Mods(score.mods)

        beatmap_difficulty = await self.calculate_difficulty(beatmap_file, score.mode, mods)
        fc_pp = await self.calculate_fc_pp(score)

        if_fc_text = ""
        mode_text = mode.formatted
        mods_text = mods.short
        stars_text = (
            f"{beatmap_difficulty.stars:.2f}★"
            if beatmap_difficulty else "N/A"
        )

        if not score.perfect:
            if_fc_text = f"({fc_pp:.2f}pp if FC)"

        embed = Embed(
            title=f"[{stars_text}] {score.beatmap.full_name} +{mods_text} ({mode_text})",
            url=f"http://osu.{config.DOMAIN_NAME}/b/{score.beatmap_id}",
            color=Color.blue(),
        )
        embed.set_author(name=f"Recent score for {user.name}", icon_url=f"https://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
        embed.set_thumbnail(url=f"https://osu.{config.DOMAIN_NAME}/mt/{score.beatmap.set_id}l")
        embed.description = (
            f"{score.grade} {score.max_combo}/{score.beatmap.max_combo} "
            f"{score.acc*100:.2f}% [{score.n300}/{score.n100}/{score.n50}/{score.nMiss}] "
            f"{score.pp:.2f}pp {if_fc_text} {score.total_score:,}"
        )
        return embed

async def setup(bot: Bot):
    await bot.add_cog(RecentScore())
