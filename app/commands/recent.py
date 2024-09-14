
from app.common.database.repositories import users, scores
from app.common.database.objects import DBScore
from app.common.constants import Mods
from app.objects import Context

from titanic_pp_py import Calculator, Beatmap
from typing import Optional, Tuple

from discord.ui import View, Button
from discord import Interaction
from discord import Embed
from discord import Color

import discord
import config
import math
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

@app.session.commands.register(["recent", "last", "r"])
async def recent(context: Context):
    """(username) - Displays the last play of another person or yourself"""
    with app.session.database.managed_session() as session:
        if not (user := users.fetch_by_discord_id(context.message.author.id, session=session)):
            await context.message.channel.send("You don't have an account linked!")
            return

        if context.args:
            if not (user := users.fetch_by_name_extended(context.args[0], session=session)):
                await context.message.channel.send("User not found!")
                return

        score_list = scores.fetch_recent_all(
            user_id=user.id,
            limit=1,
            session=session
        )

        if not score_list:
            await context.message.channel.send("No recent scores.")
            return

        score = score_list[0]
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

        if_fc_fmt = ""
        fc_pp, stars = get_difficulty_info(score)

        if score.nMiss > 0 or (score.beatmap.max_combo - score.max_combo) > 10:
            if_fc_fmt = f"({fc_pp:.2f}pp if FC)"

        stars_fmt = f"{stars:0.1f}⭐"
        mode_fmt = ('osu!', 'Taiko', 'Ctb', 'Mania')[score.mode]

        embed = Embed(
            title=f"[{stars_fmt}] {score.beatmap.beatmapset.full_name} [{score.beatmap.version}] +{mods} ({mode_fmt})",
            url=f"http://osu.{config.DOMAIN_NAME}/b/{score.beatmap_id}",
            color=Color.blue(),
        )

        embed.set_author(name=f"Recent play for {user.name}")
        embed.set_thumbnail(url=f"https://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{score.beatmap.set_id}/covers/cover@2x.jpg")

        if score.status < 2:
            rank = f"F ({int((score.failtime/1000)/score.beatmap.total_length*100)}%)"

        embed.description = f"{rank} {max_combo}/{score.beatmap.max_combo} {accuracy*100:.2f}% [{n300}/{n100}/{n50}/{nmiss}] {pp:.2f}pp {if_fc_fmt} {nscore:,}"
        replay = None

        if score.mode == 0 and app.session.storage.get_replay(score.id):
            replay = ViewReplayButton(score)

        await context.message.channel.send(
            embed=embed, reference=context.message, mention_author=True,
            view=replay
        )

def get_difficulty_info(score: DBScore) -> Tuple[float, float]:
    """Get difficulty info for fc_pp and star rating"""
    beatmap_file = app.session.storage.get_beatmap(score.beatmap_id)

    if not beatmap_file:
        app.session.logger.error(
            f'pp calculation failed: Beatmap file was not found! ({score.user_id})'
        )
        return 0.0, 0.0

    bm = Beatmap(bytes=beatmap_file)
    mods = Mods(score.mods)

    if Mods.Nightcore in mods and not Mods.DoubleTime in mods:
        # NC somehow only appears with DT enabled at the same time...?
        # https://github.com/ppy/osu-api/wiki#mods
        mods |= Mods.DoubleTime

    calc = Calculator(
        mode = score.mode,
        mods = mods.value,
        n_geki = score.nGeki,
        n_katu = score.nKatu,
        n300 = score.n300,
        n100 = score.n100,
        n50 = score.n50
    )

    if not (result := calc.performance(bm)):
        app.session.logger.error(
            'pp calculation failed: No result'
        )
        return 0.0, 0.0

    if math.isnan(result.pp) or math.isinf(result.pp):
        app.session.logger.error(
            'pp calculation failed: NaN pp'
        )
        return 0.0, 0.0

    return result.pp, result.difficulty.stars
