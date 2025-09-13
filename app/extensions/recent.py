
from app.common.database.repositories import scores
from app.common.database.objects import DBScore
from discord.ext.commands import Bot
from discord.ext import commands
from app.cog import BaseCog
from typing import List

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

        score = score_list[0]
        # TODO: Implement embed

        return await ctx.send(
            f"Embed is not implemented yet. (Score ID: {score.id})",
            reference=ctx.message,
            ephemeral=True
        )

    async def fetch_recent_scores(self, user_id: int, limit: int = 3) -> List[DBScore]:
        return await self.run_async(
            scores.fetch_recent_all,
            user_id, limit
        )

async def setup(bot: Bot):
    await bot.add_cog(RecentScore())
