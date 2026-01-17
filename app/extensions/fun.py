
from discord.ext.commands import Cog, Bot
from app.cog import BaseCog

import discord
import time
import re

class NeverKillYourself(BaseCog):
    def __init__(self) -> None:
        super().__init__()
        self.url = "https://cdn.titanic.sh/public/videos/kms.mp4"
        self.trigger = [re.compile(r"\bkms\b"), re.compile(r"\bkill(ing)? myself\b"), re.compile(r"\bkill(ing)? me\b")]
        self.last_event = time.time() - 60*5

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if (time.time() - self.last_event) < 60*5:
            return

        if not any(pattern.search(message.content) for pattern in self.trigger):
            return

        await message.channel.send(
            self.url,
            mention_author=True,
            reference=message
        )
        self.last_event = time.time()
        self.logger.info(f'"{message.author.name}" should never kill themselves')

async def setup(bot: Bot):
    await bot.add_cog(NeverKillYourself())
