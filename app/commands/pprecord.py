
from app.common.database.objects import DBScore, DBBeatmap
from app.common.constants import Mods
from app.objects import Context

from discord import Embed
from discord import Color

from typing import List

import config
import app

@app.session.commands.register(["pprecord"])
async def pp_record(context: Context):
    """Displays pp record"""
    
    def top_score(mode: int, mods: int, exclude: List[int] = []):
        with app.session.database.session as session:
            query = session.query(DBScore).filter(
                DBScore.mode == mode,
                DBScore.status == 3,
            )
            if mods:
                query = query.filter(DBScore.mods.op("&")(mods) > 0)
            for mod in exclude:
                query = query.filter(DBScore.mods.op("&")(mod) == 0)
            return query.order_by(DBScore.pp.desc()).first()

    def format_score(score: DBScore):
        if not score:
            return "No score for this mode :("
        beatmap: DBBeatmap = score.beatmap
        score_str = f"{beatmap.full_name} +{Mods(score.mods).short}\n{score.pp}pp {score.acc*100:.0f}%"
        score_str += f" {score.grade} [{score.n300}/{score.n100}/{score.n50}/{score.nMiss}]"
        user_str = f"[{score.user.name}](http://osu.{config.DOMAIN_NAME}/u/{score.user_id})"
        return f"{score_str} by {user_str}"
    
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

    mania = top_score(mode=3, mods=0)
    
    embed = Embed(title="PP Records")
    embed.add_field(name="Standard VN", value=format_score(standard[0]), inline=False)
    embed.add_field(name="Standard RX", value=format_score(standard[1]), inline=False)
    embed.add_field(name="Standard AP", value=format_score(standard[2]), inline=False)
    embed.add_field(name="Taiko VN", value=format_score(taiko[0]), inline=False)
    embed.add_field(name="Taiko RX", value=format_score(taiko[1]), inline=False)
    embed.add_field(name="Catch the beat VN", value=format_score(ctb[0]), inline=False)
    embed.add_field(name="Catch the beat RX", value=format_score(ctb[1]), inline=False)
    embed.add_field(name="Mania", value=format_score(mania), inline=False)

    await context.message.reply(embed=embed)