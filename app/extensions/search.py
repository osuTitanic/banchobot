
from config import DOMAIN_NAME
from discord.ext.commands import Bot
from discord.ext import commands
from discord import Embed

from app.common.constants import BeatmapGenre, BeatmapLanguage, DatabaseStatus
from app.common.database.repositories import beatmapsets
from app.common.database.objects import DBBeatmapset
from app.cog import BaseCog

class SearchBeatmapset(BaseCog):
    @commands.hybrid_command("search", description="Search for a beatmapset")
    async def search(
        self,
        ctx: commands.Context,
        *, query: str
    ) -> None:
        async with ctx.typing():
            if not (beatmapset := await self.search_beatmapset(query)):
                return await ctx.send(
                    'No maps for this query were found.',
                    reference=ctx.message,
                    ephemeral=True
                )

            await ctx.send(embed=self.create_embed(beatmapset))

    def create_embed(self, beatmapset: DBBeatmapset) -> Embed:
        embed = Embed(title=beatmapset.full_name, url=f"http://osu.{DOMAIN_NAME}/s/{beatmapset.id}", description="")
        embed.set_thumbnail(url=self.thumbnail_url(beatmapset))
        embed.add_field(name="Title", value=beatmapset.title)
        embed.add_field(name="Artist", value=beatmapset.artist)
        embed.add_field(name="Creator", value=beatmapset.creator)
        embed.add_field(name="Status", value=DatabaseStatus(beatmapset.status).name)
        embed.add_field(name="Genre", value=BeatmapGenre(beatmapset.genre_id).name)
        embed.add_field(name="Language", value=BeatmapLanguage(beatmapset.language_id).name)
        return embed

    async def search_beatmapset(self, query: str) -> DBBeatmapset | None:
        return await self.run_async(
            beatmapsets.search_one,
            query
        )

async def setup(bot: Bot):
    await bot.add_cog(SearchBeatmapset())
