
from app.common.database.repositories import users
from app.common.database.objects import DBUser
from discord.ext.commands import Bot
from discord.ext import commands
from app.cog import BaseCog

class Profile(BaseCog):
    @commands.hybrid_command("profile", description="Display the profile of you or another person", aliases=["stats", "show"])
    async def profile(self, ctx: commands.Context, username: str | None = None) -> None:
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

        return await ctx.send(
            f"Embed is not implemented yet. (User ID: {user.id})",
            reference=ctx.message,
            ephemeral=True
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

async def setup(bot: Bot):
    await bot.add_cog(Profile())
