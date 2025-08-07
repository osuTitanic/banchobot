
import discord
import config
import shlex
import app
import re

class BanchoBot(discord.Client):
    async def on_ready(self):
        app.session.logger.info(f'Logged in as {self.user}.')
        app.session.filters.populate()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = BanchoBot(intents=intents)

def run():
    app.session.bot = client
    client.run(config.BOT_TOKEN, log_handler=None)
