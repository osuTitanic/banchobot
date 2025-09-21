
from app.common.database.repositories import scores
from app.common.database.objects import DBScore
from app.extensions.types import *
from discord.ext.commands import Bot
from discord.ext import commands
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
            f"Embed is not implemented yet. ({len(user_scores)} scores)",
            reference=ctx.message,
            ephemeral=True
        )

    async def fetch_top_scores(self, user_id: int, mode: int, limit: int = 100) -> List[DBScore]:
        return await self.run_async(
            scores.fetch_top_scores,
            user_id, mode, True, limit
        )

async def setup(bot: Bot):
    await bot.add_cog(TopScores())
