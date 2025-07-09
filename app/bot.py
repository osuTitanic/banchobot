
from app.common.constants.regexes import MARKDOWN_LINK, DISCORD_EMOTE
from app.common.database.repositories import users, messages
from app.objects import Context

import discord
import config
import shlex
import app
import re

BEATMAP_URLS = ("https://osu.ppy.sh/b/", "https://osu.ppy.sh/beatmapsets/", "https://osu.ppy.sh/s/", f"https://{config.DOMAIN_NAME}/b/", f"https://{config.DOMAIN_NAME}/beatmapsets/", f"https://{config.DOMAIN_NAME}/s/")

class BanchoBot(discord.Client):
    async def on_ready(self):
        app.session.logger.info(
            f'Logged in as {self.user}.'
        )

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if config.CHAT_CHANNEL_ID and message.channel.id == config.CHAT_CHANNEL_ID:
            return self.handle_bancho_chat(message)

        if not message.content.startswith(config.BOT_PREFIX):
            return

        # Parse command
        trigger, *args = shlex.split(message.content.strip()[1:])

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

        async with message.channel.typing():
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

    def handle_bancho_chat(self, message: discord.Message) -> None:
        with app.session.database.managed_session() as session:
            target_user = users.fetch_by_discord_id(
                message.author.id,
                session=session
            )

            if not target_user:
                return app.session.logger.warning(
                    f'User {message.author} ({message.author.id}) tried to send a message '
                    f'in the #osu channel, but is not registered in the database.'
                )
                
            if target_user.silence_end:
                return app.session.logger.warning(
                    f'User {message.author} ({message.author.id}) tried to send a message '
                    f'in the #osu channel, but is silenced.'
                )
                
            if target_user.restricted:
                return app.session.logger.warning(
                    f'User {message.author} ({message.author.id}) tried to send a message '
                    f'in the #osu channel, but is restricted.'
                )

            message_target = config.CHAT_WEBHOOK_CHANNELS[0]
            message_content = message.content.strip()

            # Replace username mentions with usernames
            for mention in message.mentions:
                message_content = message_content.replace(
                    mention.mention,
                    f'@{mention.name}'
                )

            # Replace role mentions with role names
            for role in message.role_mentions:
                message_content = message_content.replace(
                    role.mention,
                    f'@{role.name}'
                )

            # Replace discord emotes with text representation
            for match in re.finditer(DISCORD_EMOTE, message_content):
                emote_text = match.group(0)
                emote_name = match.group(1)
                message_content = message_content.replace(
                    emote_text,
                    f':{emote_name}:'
                )

            # If message is replying to another message, include the reply target
            if message.reference:
                message_content = (
                    f'(Reply): {message_content}'
                )

            if message.attachments:
                message_content += (
                    f' ({len(message.attachments)}'
                    f' attachment{"s" if len(message.attachments) > 1 else ""})'
                )

            if not message_content:
                return

            if len(message_content) > 512:
                message_content = message_content[:509] + '...'

            app.session.events.submit(
                'external_message',
                target_user.id,
                target_user.name,
                message_target,
                message_content,
                submit_to_webhook=False
            )

            messages.create(
                target_user.name,
                message_target,
                message_content,
                session=session
            )

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = BanchoBot(intents=intents)

def run():
    app.session.bot = client
    client.run(config.BOT_TOKEN, log_handler=None)
