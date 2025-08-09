
from discord.ext.commands import *
from app.commands import *

import discord
import config
import app

class BanchoBot(Bot):
    async def on_ready(self):
        app.session.logger.info(f'Logged in as {self.user}.')
        app.session.filters.populate()
        await self.load_cogs()
        
    async def load_cogs(self):
        await self.load_extension("app.commands.kms")

def run():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    app.session.bot = BanchoBot(config.BOT_PREFIX, intents=intents)
    app.session.bot.run(config.BOT_TOKEN, log_handler=None)
