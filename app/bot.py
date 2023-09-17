
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
            # Command requires permissions
            author_roles = [role.name for role in message.author.roles]

            for role in command.roles:
                if role in author_roles:
                    break
            else:
                # User doesn't have any of the required roles
                app.session.logger.warning(
                    f"[{message.author}] -> Tried to execute command {config.BOT_PREFIX}{trigger} but doesn't have the role for it"
                )
                await message.channel.send(
                    'Your are not permitted to use that command.',
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
