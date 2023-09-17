
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
            f'[{message.author}] -> !{trigger}: {args}'
        )

        if not (command := app.session.commands.get(trigger)):
            await message.channel.send(
                f'Could not find that command. Type {config.BOT_PREFIX}help for a list of commands!',
                mention_author=True
            )
            return

        # Try to execute command
        await command.function(
            Context(trigger, args, message)
        )

intents = discord.Intents.default()
intents.message_content = True
client = BanchoBot(intents=intents)

def run():
    client.run(config.BOT_TOKEN, log_handler=None)
