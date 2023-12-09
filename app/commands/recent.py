
from app.common.database.repositories import users, scores
from app.common.database.objects import DBScore
from app.common.constants import Mods
from app.objects import Context
from typing import Optional

from discord.ui import View, Button
from discord import ButtonStyle
from discord import Interaction
from discord import Embed
from discord import Color

import discord
import config
import app
import io


class ViewReplayButton(View):
    def __init__(self, score: DBScore, *, timeout: Optional[float] = 250):
        super().__init__(timeout=timeout)
        self.score = score

    @discord.ui.button(label='View Replay')
    async def view_replay(self, interaction: Interaction, button: Button):
        if button.disabled:
            return

        async with interaction.channel.typing():
            replay = app.session.storage.get_full_replay(self.score.id)

            if not replay:
                await interaction.response.send_message(
                    'Replay could not be found.'
                )
                return

            button.disabled = True

            await interaction.response.send_message(
                file=discord.File(io.BytesIO(replay), filename=f'{self.score.id}.osr')
            )

            await interaction.message.edit(view=self)

@app.session.commands.register(["recent", "last"])
async def recent(context: Context):
    """<username> Displays your last play"""
    if not (user := users.fetch_by_discord_id(context.message.author.id)):
        await context.message.channel.send("You don't have an account linked!")
        return

    if len(context.args):
        if not (user := users.fetch_by_name(context.args[0])):
            await context.message.channel.send("User not found!")
            return

    score = scores.fetch_recent_all(user_id=user.id, limit=1)

    if not score:
        await context.message.channel.send("No recent scores.")
        return

    score = score[0]

    rank = score.grade
    max_combo = score.max_combo
    accuracy = score.acc
    n300 = score.n300
    n100 = score.n100
    n50 = score.n50
    nmiss = score.nMiss
    pp = score.pp
    nscore = score.total_score
    mods = Mods(score.mods).short

    embed = Embed(
        title=f"{score.beatmap.beatmapset.full_name} [{score.beatmap.version}] +{mods}",
        url=f"http://osu.{config.DOMAIN_NAME}/b/{score.beatmap_id}",
        color=Color.blue(),
    )
    embed.set_author(name=f"Recent play for {user.name}")
    embed.set_thumbnail(url=f"https://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
    embed.set_image(
        url=f"https://assets.ppy.sh/beatmaps/{score.beatmap.set_id}/covers/cover@2x.jpg"
    )

    if score.status < 2:
        rank = f"F ({int((score.failtime/1000)/score.beatmap.total_length*100)}%)"

    embed.description = f"{rank} {max_combo}/{score.beatmap.max_combo} {accuracy*100:.2f}% [{n300}/{n100}/{n50}/{nmiss}] {pp:.2f}pp {nscore:,}"
    replay = None

    if score.mode == 0 and app.session.storage.get_replay(score.id):
        replay = ViewReplayButton(score)

    await context.message.channel.send(
        embed=embed, reference=context.message, mention_author=True,
        view=replay
    )
