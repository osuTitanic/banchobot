
from discord import Interaction, app_commands
from discord.ext.commands import *
from app.cog import BaseCog

class ErrorHandler(BaseCog):
    def log_unexpected_error(self, message: str, error: Exception) -> None:
        self.logger.error(
            message,
            exc_info=(type(error), error, error.__traceback__)
        )

    async def send_interaction_error(
        self,
        interaction: Interaction,
        message: str
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
            return

        await interaction.response.send_message(message, ephemeral=True)

    async def on_app_command_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            return await self.send_interaction_error(
                interaction,
                "You don't have permission to use this command."
            )

        if isinstance(error, app_commands.CheckFailure):
            return await self.send_interaction_error(
                interaction,
                "You don't have permission to use this command."
            )

        if isinstance(error, app_commands.CommandOnCooldown):
            return await self.send_interaction_error(
                interaction,
                f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            )

        original_error = getattr(error, "original", error)
        self.log_unexpected_error("Unexpected app command error.", original_error)

        await self.send_interaction_error(
            interaction,
            "An unexpected error occurred while running this command."
        )

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

        elif isinstance(error, CheckFailure):
            return await ctx.send("You don't have permission to use this command.")

        elif isinstance(error, CommandOnCooldown):
            return await ctx.send(
                f"This command is on cooldown. Try again in "
                f"{error.retry_after:.1f} seconds."
            )

        # Log unexpected errors
        original_error = getattr(error, "original", error)
        self.log_unexpected_error("Unexpected command error.", original_error)
        await ctx.send("An unexpected error occurred while running this command.")

async def setup(bot: Bot):
    cog = ErrorHandler()
    await bot.add_cog(cog)
    bot.tree.on_error = cog.on_app_command_error
