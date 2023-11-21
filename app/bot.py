
from app.common.database.repositories import users
from app.objects import Context
from discord.utils import get

import discord
import config
import app

class BanchoBot(discord.Client):
    async def on_ready(self):
        app.session.logger.info(
            f'Logged in as {self.user}.'
        )

    async def on_message(self, message: discord.Message):
        if not message.content.startswith(config.BOT_PREFIX):
            return

        if message.author.bot:
            return

        # Parse command
        trigger, *args = message.content.strip()[1:].split()

        app.session.logger.info(
            f'[{message.author}] -> {config.BOT_PREFIX}{trigger}: {args}'
        )

        if not (command := app.session.commands.get(trigger)):
            await message.channel.send(
                f'Could not find that command. Type {config.BOT_PREFIX}help for a list of commands!',
                mention_author=True,
                reference=message
            )
            return

        # Check command roles
        if not command.has_permission(message.author):
            # User doesn't have any of the required roles
            app.session.logger.warning(
                f"[{message.author}] -> Tried to execute command {config.BOT_PREFIX}{trigger} but doesn't have the role for it"
            )
            await message.channel.send(
                'You are not permitted to use that command.',
                mention_author=True,
                reference=message
            )
            return

        try:
            # Try to execute command
            await command.function(
                Context(trigger, args, message)
            )
        except Exception as e:
            app.session.logger.error(
                f'Failed to execute command {config.BOT_PREFIX}{trigger}: {e}',
                exc_info=e
            )
            await message.channel.send(
                'An error occured while running this command.',
                mention_author=True,
                reference=message
            )

    async def on_member_join(self, member: discord.Member):
        app.session.logger.info(
            f'New member joined the server: {member}'
        )

        if not (setup := get(member.guild.channels, name='setup')):
            app.session.logger.warning(
                'Failed to get #setup channel! Aborting join event.'
            )
            return

        dm = await member.create_dm()

        # Check if user already has an account
        if user := users.fetch_by_discord_id(member.id):
            app.session.logger.info(
                f'Member "{member}" already has a linked account: {user.name}'
            )

            # Assign member role
            await member.add_roles(
                get(member.guild.roles, name='Member')
            )

            await dm.send(
                content="🎉 Welcome Aboard to osuTitanic! 🚢\n\n"
                        "Ahoy! We are glad to have you on board here.\n"
                        "It seems that you already have an account linked to your discord profile, so we've added the Member role to your profile.\n"
                       f"To get started you can view the <#{setup.id}> channel.\n\n"
                        "Feel free to ask us any questions and enjoy your stay!"
            )
            return

        await dm.send(
            content="🎉  Welcome Aboard to osuTitanic!\n\n"
                    "Ahoy! We are glad to have you on board here.\n"
                   f"It seems that you are new here. To get started you can view the <#{setup.id}> channel.\n\n"
                    "Feel free to ask us any questions and enjoy your stay!"
        )

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = BanchoBot(intents=intents)

def run():
    app.session.bot = client
    client.run(config.BOT_TOKEN, log_handler=None)
