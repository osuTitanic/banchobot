
from app.common.constants import BeatmapGenre, BeatmapLanguage
from app.common.database.repositories import beatmapsets
from app.common.database import DBBeatmapset
from app.objects import Context

from discord import Embed, Interaction, Button
from discord.ui import View

import discord
import config
import app

def create_embed(set: DBBeatmapset) -> Embed:
    status = {
        -2: 'Graveyarded',
        -1: 'WIP',
         0: 'Pending',
         1: 'Ranked',
         2: 'Approved',
         3: 'Qualified',
         4: 'Loved'
    }[set.status]

    embed = Embed(title=set.full_name, url=f'http://osu.{config.DOMAIN_NAME}/s/{set.id}', description='')
    embed.set_image(url=f'https://assets.ppy.sh/beatmaps/{set.id}/covers/cover@2x.jpg')
    embed.add_field(name='Title', value=set.title)
    embed.add_field(name='Artist', value=set.artist)
    embed.add_field(name='Creator', value=set.creator)
    embed.add_field(name='Status', value=status)
    embed.add_field(name='Genre', value=BeatmapGenre(set.genre_id).name)
    embed.add_field(name='Language', value=BeatmapLanguage(set.language_id).name)

    return embed

class NextButton(View):
    def __init__(self, *, query: str, timeout: int = 60, offset: int = 0):
        super().__init__(timeout=timeout)
        self.offset = offset
        self.query = query

    @discord.ui.button(label='Next', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button: Button):
        app.session.logger.info(
            f'[{interaction.user}] -> Pressed next button...'
        )

        self.offset += 1

        set = beatmapsets.search_one(self.query, self.offset)

        if not set:
            return

        app.session.logger.info(
            f'[{interaction.user}] -> Found beatmap: "{set.full_name}"'
        )

        await interaction.response.edit_message(
            embed=create_embed(set),
            view=NextButton(
                query=self.query,
                timeout=30,
                offset=self.offset
            )
        )

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, button: Button):
        app.session.logger.info(
            f'[{interaction.user}] -> Pressed previous button...'
        )

        if self.offset <= 0:
            return

        self.offset -= 1

        set = beatmapsets.search_one(self.query, self.offset)

        if not set:
            return

        app.session.logger.info(
            f'[{interaction.user}] -> Found beatmap: "{set.full_name}"'
        )

        await interaction.response.edit_message(
            embed=create_embed(set),
            view=NextButton(
                query=self.query,
                timeout=30,
                offset=self.offset
            )
        )

@app.session.commands.register(['search', 's'])
async def search(context: Context):
    """Search up a beatmap"""

    async with context.message.channel.typing():
        query = ' '.join(context.args)

        app.session.logger.info(
            f'[{context.message.author}] -> Requesting beatmap: "{query}"'
        )

        if len(query) <= 3:
            await context.message.channel.send(
                'Query too short!'
            )
            return

        set = beatmapsets.search_one(query)

        if not set:
            await context.message.channel.send(
                'No maps were found!'
            )
            return

        app.session.logger.info(
            f'[{context.message.author}] -> Found beatmap: "{set.full_name}"'
        )

        await context.message.channel.send(
            embed=create_embed(set),
            view=NextButton(
                query=query,
                timeout=30,
                offset=1
            )
        )
