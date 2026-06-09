from discord.ext.commands import *
from app.extensions import *

import discord
import app

class BanchoBot(Bot):
    async def on_ready(self):
        app.session.logger.info(f'Logged in as {self.user}.')
        app.session.filters.populate()
        await self.load_cogs()

    async def close(self):
        app.session.redis.close()
        app.session.database.engine.dispose()
        await app.session.redis_async.close()
        await super().close()

    async def load_cogs(self):
        await self.load_extension_safe("app.extensions.errors")
        await self.load_extension_safe("app.extensions.bridge")
        await self.load_extension_safe("app.extensions.link")
        await self.load_extension_safe("app.extensions.fun")
        await self.load_extension_safe("app.extensions.recent")
        await self.load_extension_safe("app.extensions.profile")
        await self.load_extension_safe("app.extensions.top")
        await self.load_extension_safe("app.extensions.simulate")
        await self.load_extension_safe("app.extensions.search")
        await self.load_extension_safe("app.extensions.rankings")
        await self.load_extension_safe("app.extensions.pprecord")
        await self.load_extension_safe("app.extensions.moderation")
        await self.load_extension_safe("app.extensions.beatmaps")
        await self.sync_tree_safe()

    async def load_extension_safe(self, extension: str):
        try:
            await self.load_extension(extension)
            app.session.logger.info(f'Loaded extension: {extension}')
        except Exception as e:
            app.session.logger.error(f'Failed to load extension {extension}: {e}')

    async def sync_tree_safe(self):
        try:
            await self.tree.sync()
            app.session.logger.info('Command tree synced successfully')
        except Exception as e:
            app.session.logger.error(f'Failed to sync command tree: {e}')

def run():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    app.session.bot = BanchoBot(app.session.config.DISCORD_BOT_PREFIX, intents=intents, help_command=None)
    app.session.bot.run(app.session.config.DISCORD_BOT_TOKEN, log_handler=None)
