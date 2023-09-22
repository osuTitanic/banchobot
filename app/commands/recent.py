from app.common.database.repositories import users, scores
from app.common.database.objects import DBBeatmapset
from app.common.constants import Mods
from app.objects import Context
from discord import Embed
from discord import Color

import config
import app


@app.session.commands.register(["recent", "last"])
async def recent(context: Context):
    """Displays your last play"""
    if not (user := users.fetch_by_discord_id(context.message.author.id)):
        await context.message.channel.send("You don't have an account linked!")
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
        url="https://pbs.twimg.com/media/Dqnn54dVYAAVuki.jpg",
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

    await context.message.channel.send(
        embed=embed, reference=context.message, mention_author=True
    )
