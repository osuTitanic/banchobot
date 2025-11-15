
from discord import Embed, Interaction, Button, ButtonStyle
from discord.ext.commands import Bot
from discord.ui import View, button
from discord.ext import commands
from config import DOMAIN_NAME

from app.common.constants import BeatmapGenre, BeatmapLanguage, BeatmapStatus
from app.common.database.repositories import beatmapsets
from app.common.database.objects import DBBeatmapset
from app.cog import BaseCog

class Search(BaseCog):
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

            await ctx.send(
                embed=self.create_embed(beatmapset),
                view=NextButton(query=query, timeout=30)
            )

    @classmethod
    async def search_beatmapset(cls, query: str, offset: int = 0) -> DBBeatmapset | None:
        return await cls.run_async(
            beatmapsets.search_one,
            query, offset
        )

    @classmethod
    def create_embed(cls, beatmapset: DBBeatmapset) -> Embed:
        embed = Embed(title=beatmapset.full_name, url=f"http://osu.{DOMAIN_NAME}/s/{beatmapset.id}", description="")
        embed.set_thumbnail(url=cls.thumbnail_url(beatmapset))
        embed.add_field(name="Title", value=beatmapset.title)
        embed.add_field(name="Artist", value=beatmapset.artist)
        embed.add_field(name="Creator", value=beatmapset.creator)
        embed.add_field(name="Status", value=BeatmapStatus(beatmapset.status).name)
        embed.add_field(name="Genre", value=BeatmapGenre(beatmapset.genre_id).name)
        embed.add_field(name="Language", value=BeatmapLanguage(beatmapset.language_id).name)
        return embed

class NextButton(View):
    def __init__(self, *, query: str, timeout: int = 60, offset: int = 0):
        super().__init__(timeout=timeout)
        self.offset = offset
        self.query = query

    @button(label='Next', style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button: Button):
        self.offset += 1

        if not (set := await Search.search_beatmapset(self.query, self.offset)):
            return

        await interaction.response.edit_message(
            embed=Search.create_embed(set),
            view=self
        )

    @button(label='Previous', style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, button: Button):
        if self.offset <= 0:
            return

        self.offset -= 1

        if not (set := await Search.search_beatmapset(self.query, self.offset)):
            return

        await interaction.response.edit_message(
            embed=Search.create_embed(set),
            view=self
        )

async def setup(bot: Bot):
    await bot.add_cog(Search())
