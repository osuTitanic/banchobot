from app.common.database.repositories import scores
from app.common.database.objects import DBScore
from app.common.constants import Mods
from app.objects import Context

from discord import Embed
from discord import Color

from typing import List

import config
import app

def top_score(mode: int, mods: int, exclude: List[int] = []) -> DBScore:
    with app.session.database.managed_session() as session:
        query = session.query(DBScore).filter(
            DBScore.mode == mode,
            DBScore.status == 3
        )
        if mods:
            query = query.filter(DBScore.mods.op("&")(mods) > 0)
        for mod in exclude:
            query = query.filter(DBScore.mods.op("&")(mod) == 0)
        return query.order_by(DBScore.pp.desc()).first()

@app.session.commands.register(["pprecord"])
async def pp_record(context: Context):
    """(mods) - Displays pp record"""

    def format_score(score: DBScore):
        if not score:
            return "No score for this mode :("
        score_str = f"{score.beatmap.full_name} +{Mods(score.mods).short}\n{score.pp:.2f}pp {score.acc*100:.2f}%"
        score_str += f" {score.grade} [{score.n300}/{score.n100}/{score.n50}/{score.nMiss}]"
        user_str = f"[{score.user.name}](http://osu.{config.DOMAIN_NAME}/u/{score.user_id})"
        return f"{score_str} by {user_str}"

    if context.args:
        embed = Embed(title="PP Records", color=Color.blue())
        records = [scores.fetch_pp_record(mode, Mods.from_string(context.args[0])) for mode in range(4)]
        if records[0]:
            embed.add_field(name="Standard", value=format_score(records[0]), inline=False)
        if records[1]:
            embed.add_field(name="Taiko", value=format_score(records[1]), inline=False)
        if records[2]:
            embed.add_field(name="Catch the beat", value=format_score(records[2]), inline=False)
        if records[3]:
            embed.add_field(name="Mania", value=format_score(records[3]), inline=False) 
        await context.message.reply(embed=embed)
        return

    standard = (
        top_score(mode=0, mods=0, exclude=[Mods.Relax, Mods.Autopilot]),
        top_score(mode=0, mods=Mods.Relax),
        top_score(mode=0, mods=Mods.Autopilot),
    )

    taiko = (
        top_score(mode=1, mods=0, exclude=[Mods.Relax]),
        top_score(mode=1, mods=Mods.Relax),
    )

    ctb = (
        top_score(mode=2, mods=0, exclude=[Mods.Relax]),
        top_score(mode=2, mods=Mods.Relax),
    )

    mania = top_score(
        mode=3,
        mods=0
    )

    embed = Embed(title="PP Records", color=Color.blue())
    embed.add_field(name="Standard VN", value=format_score(standard[0]), inline=False)
    embed.add_field(name="Standard RX", value=format_score(standard[1]), inline=False)
    embed.add_field(name="Standard AP", value=format_score(standard[2]), inline=False)
    embed.add_field(name="Taiko VN", value=format_score(taiko[0]), inline=False)
    embed.add_field(name="Taiko RX", value=format_score(taiko[1]), inline=False)
    embed.add_field(name="Catch the beat VN", value=format_score(ctb[0]), inline=False)
    embed.add_field(name="Catch the beat RX", value=format_score(ctb[1]), inline=False)
    embed.add_field(name="Mania", value=format_score(mania), inline=False)

    await context.message.reply(embed=embed)
