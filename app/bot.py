
from discord.ext.commands import *
from app.extensions import *

import discord
import config
import app

class BanchoBot(Bot):
    async def on_ready(self):
        app.session.logger.info(f'Logged in as {self.user}.')
        app.session.filters.populate()
        await self.load_cogs()

    async def load_cogs(self):
        await self.load_extension("app.extensions.errors")
        await self.load_extension("app.extensions.bridge")
        await self.load_extension("app.extensions.link")
        await self.load_extension("app.extensions.fun")
        await self.load_extension("app.extensions.recent")
        await self.load_extension("app.extensions.profile")
        await self.load_extension("app.extensions.top")
        await self.load_extension("app.extensions.simulate")
        await self.load_extension("app.extensions.search")
        await self.load_extension("app.extensions.rankings")
        await self.tree.sync()

def run():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    app.session.bot = BanchoBot(config.BOT_PREFIX, intents=intents, help_command=None)
    app.session.bot.run(config.BOT_TOKEN, log_handler=None)
