
from discord.ext.commands import *
from app.cog import BaseCog

class ErrorHandler(BaseCog):
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        if hasattr(ctx.command, "on_error"):
            # Ignore errors that already have a local handler
            return

        if isinstance(error, CommandNotFound):
            return

        elif isinstance(error, MissingRequiredArgument):
            return await ctx.send(f"Missing argument: `{error.param.name}`")

        elif isinstance(error, MissingPermissions):
            return await ctx.send("You don't have permission to use this command.")

        elif isinstance(error, CommandOnCooldown):
            return await ctx.send(
                f"This command is on cooldown. Try again in "
                f"{error.retry_after:.1f} seconds."
            )

        # Log unexpected errors
        self.logger.error(f'Unexpected error: {error}', exc_info=True)
        await ctx.send("An unexpected error occurred.")

async def setup(bot: Bot):
    await bot.add_cog(ErrorHandler())
