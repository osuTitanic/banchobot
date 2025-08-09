
from discord.ext.commands import Cog, Bot
from discord.ui import Modal, TextInput
from discord.ext import commands
from discord import app_commands

from app.common.database.objects import DBUser
from app.common.cache import status
from app.cog import BaseCog

import discord
import random
import string
import time

class AccountLinking(BaseCog):
    def __init__(self) -> None:
        super().__init__()
        self.member_role = discord.utils.get(self.guild.roles, name="Member")

    @commands.hybrid_command("link", description="Link your account to Titanic!", hidden=True)
    async def link_account(self, ctx: commands.Context, username: str) -> None:
        if existing_user := await self.resolve_user(ctx.author.id):
            return await ctx.send(
                "Your account is already linked to Titanic! "
                "Use /unlink to unlink your current account.",
                ephemeral=True
            )

        if not (target_user := await self.resolve_user_by_name(username)):
            return await ctx.send(
                "No user found with that name.",
                ephemeral=True
            )

        if target_user.discord_id:
            return await ctx.send(
                "This user is already linked to another Discord account.",
                ephemeral=True
            )

        if not status.exists(target_user.id):
            return await ctx.send(
                "Please log into the game and try again!",
                ephemeral=True
            )

        self.logger.info(f'[{ctx.author}] -> Starting linking process...')

        # Generate random 6-letter code which will be sent over DMs
        code = ''.join(random.choices(string.ascii_lowercase, k=6))
        await self.submit_event('link', target_user.id, code)

        embed = discord.Embed(
            title="🔗 Link Your Account",
            description=(
                f"You are linking the account: **{target_user.name}**\n"
                "Click the button below to enter your code."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="This message is only visible to you.")

        await ctx.send(
            view=LinkingView(code, target_user, self),
            embed=embed,
            ephemeral=True
        )

    @commands.hybrid_command("unlink", description="Unlink your account from Titanic!", hidden=True)
    async def unlink_account(self, ctx: commands.Context) -> None:
        if not (linked_user := await self.resolve_user(ctx.author.id)):
            return await ctx.send(
                "Your account is not linked to Titanic!",
                ephemeral=True
            )

        await self.update_user(
            linked_user.id,
            {"discord_id": None}
        )
        await ctx.send(
            "You have successfully unlinked your account from Titanic!",
            ephemeral=True
        )

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Try to check if user already has their account linked to Titanic!
        linked_user = await self.resolve_user(member.id)

        if not linked_user:
            return

        # Re-add member role
        await member.add_roles(self.member_role)

class LinkingView(discord.ui.View):
    def __init__(self, code: str, target_user: DBUser, cog: "AccountLinking"):
        super().__init__(timeout=60*5)
        self.target_user = target_user
        self.code = code
        self.cog = cog

    @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.primary)
    async def enter_code(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        modal = AccountLinkingModal(self.code, self.target_user, self.cog)
        await interaction.response.send_modal(modal)

class AccountLinkingModal(Modal):
    def __init__(self, valid_code: str, target_user: DBUser, cog: "AccountLinking") -> None:
        super().__init__(
            title="Link your account",
            timeout=60*5
        )
        self.code = TextInput(
            label="Enter in-game code",
            placeholder="abc123",
            required=True,
            max_length=6
        )
        self.add_item(self.code)
        self.target_user = target_user
        self.valid_code = valid_code
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.cog.logger.info(
            f'[{interaction.user}] -> Entered code: "{self.code.value}"'
        )

        if self.code.value != self.valid_code:
            return await interaction.response.send_message(
                "Invalid code. Please try again.",
                ephemeral=True
            )

        await self.cog.update_user(
            self.target_user.id,
            {"discord_id": interaction.user.id}
        )
        await interaction.response.send_message(
            "Account linked successfully!",
            ephemeral=True
        )
        self.cog.logger.info(
            f'[{interaction.user}] -> Account was linked to: {self.target_user.name}'
        )

        # Add member role to let the user access #osu chat
        await interaction.user.add_roles(self.cog.member_role)

async def setup(bot: Bot):
    await bot.add_cog(AccountLinking())
