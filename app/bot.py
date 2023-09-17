
from app.objects import Context

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

        trigger, *args = message.content.strip()[1:].split()

        app.session.logger.info(
            f'[{message.author}] -> {config.BOT_PREFIX}{trigger}: {args}'
        )

        if not (command := app.session.commands.get(trigger)):
            await message.channel.send(
                f'Could not find that command. Type {config.BOT_PREFIX}help for a list of commands!',
                mention_author=True
            )
            return

        if command.roles:
            if not command.has_permission(message.author):
                # User doesn't have any of the required roles
                app.session.logger.warning(
                    f"[{message.author}] -> Tried to execute command {config.BOT_PREFIX}{trigger} but doesn't have the role for it"
                )
                await message.channel.send(
                    'Your are not permitted to use that command.',
                    mention_author=True
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
                mention_author=True
            )

intents = discord.Intents.default()
intents.message_content = True
client = BanchoBot(intents=intents)

def run():
    client.run(config.BOT_TOKEN, log_handler=None)
