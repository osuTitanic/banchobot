
from app.common.database.repositories import messages
from app.common.database.objects import DBUser
from app.common.constants.regexes import *
from app.common.helpers import infringements
from discord.ext.commands import Cog, Bot
from app.cog import BaseCog

import discord
import config

class BanchoChatBridge(BaseCog):
    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if not config.CHAT_CHANNEL_ID:
            return

        if message.channel.id != config.CHAT_CHANNEL_ID:
            return

        target_user = await self.resolve_user(message.author.id)

        if not target_user:
            return self.logger.warning(
                f"User {message.author} ({message.author.id}) tried to send a message "
                f"in the #osu channel, but is not registered in the database."
            )

        if target_user.silence_end:
            return self.logger.warning(
                f'User {message.author} ({message.author.id}) tried to send a message '
                f'in the #osu channel, but is silenced.'
            )

        if target_user.restricted:
            return self.logger.warning(
                f'User {message.author} ({message.author.id}) tried to send a message '
                f'in the #osu channel, but is restricted.'
            )

        message_target = config.CHAT_WEBHOOK_CHANNELS[0]
        message_content = message.content.strip()
        
        # Apply chat filters
        message_content, timeout_duration = self.filters.apply(message_content)

        if timeout_duration is not None:
            return await self.silence_user(
                target_user, timeout_duration,
                "Inappropriate discussion in #osu"
            )

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
        for match in DISCORD_EMOTE.finditer(message_content):
            emote_text = match.group(0)
            emote_name = match.group(1)
            message_content = message_content.replace(
                emote_text,
                f':{emote_name}:'
            )

        # Replace markdown links with osu! style links
        for match in MARKDOWN_LINK.finditer(message_content):
            link_original_text = match.group(0)
            link_text = match.group(1)
            link_url = match.group(2)
            message_content = message_content.replace(
                link_original_text,
                f'[{link_url} {link_text}]'
            )

        # If message is replying to another message, include the reply target
        if message.reference:
            message_content = (
                f'\x01ACTION replied: {message_content}'
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

        self.logger.info(
            f'[{message_target}] {target_user.name}: "{message_content}"'
        )

        await self.submit_event(
            'external_message',
            target_user.id,
            target_user.name,
            message_target,
            message_content,
            False
        )

        await self.create_message(
            target_user.name,
            message_target,
            message_content
        )

    async def silence_user(self, user: DBUser, duration: float, reason: str) -> None:
        return await self.run_async(
            infringements.silence_user,
            user, duration, reason
        )

    async def submit_event(self, name: str, *args) -> None:
        return await self.run_async(
            self.events.submit,
            name, *args
        )

    async def create_message(self, username: str, target: str, content: str) -> None:
        return await self.run_async(
            messages.create,
            username, target, content
        )

async def setup(bot: Bot):
    await bot.add_cog(BanchoChatBridge())
