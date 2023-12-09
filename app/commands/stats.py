
from app.common.database.repositories import users
from app.common.database.objects import DBStats
from app.common.cache import leaderboards
from app.objects import Context

from discord import Embed
from discord import Color

import config
import app


@app.session.commands.register(["stats", "profile", "show"])
async def stats(context: Context):
    """<std/taiko/ctb/mania> <username> - Displays your statistics"""
    if not (user := users.fetch_by_discord_id(context.message.author.id)):
        await context.message.channel.send("You don't have an account linked!")
        return

    mode = user.preferred_mode
    modes = {"std": 0, "taiko": 1, "ctb": 2, "mania": 3}

    if len(context.args):
        if context.args[0] in modes:
            mode = modes[context.args[0]]
        else:
            await context.message.reply(
                f"Wrong mode! Available modes: {', '.join(modes.keys())}"
            )
            return
        if len(context.args) > 1:
            if not (user := users.fetch_by_name(context.args[1])):
                await context.message.channel.send("User not found!")
                return

    stats: DBStats = [stats for stats in user.stats if stats.mode == mode][0]

    embed = Embed(
        title=f"Statistics for {user.name}",
        url=f"http://osu.{config.DOMAIN_NAME}/u/{user.id}",
        color=Color.blue(),
    )

    pp_rank = leaderboards.global_rank(user.id, mode)
    ppv1_rank = leaderboards.ppv1_rank(user.id, mode)
    score_rank = leaderboards.score_rank(user.id, mode)
    tscore_rank = leaderboards.total_score_rank(user.id, mode)

    embed.add_field(name="Ranked score", value=f"{stats.rscore:,} (#{score_rank})")
    embed.add_field(name="Total score", value=f"{stats.tscore:,} (#{tscore_rank})")
    embed.add_field(name="Total hits", value=f"{stats.total_hits:,}")
    embed.add_field(name="Play count", value=f"{stats.playcount:,}")
    embed.add_field(name="Play time", value=f"{stats.playtime/60/60:,.2f}h")
    embed.add_field(name="Replay views", value=f"{stats.replay_views:,}")
    embed.add_field(name="Accuracy", value=f"{stats.acc*100:.2f}%")
    embed.add_field(name="Max combo", value=f"{stats.max_combo:,}")
    embed.add_field(name="Performance points", value=f"{stats.pp:.0f}pp, {stats.ppv1:.0f}ppv1 (#{pp_rank}, #{ppv1_rank})")
    embed.add_field(name="SS/SS+", value=f"{stats.x_count}/{stats.xh_count}")
    embed.add_field(name="S/S+", value=f"{stats.s_count}/{stats.sh_count}")
    embed.add_field(
        name="A/B/C/D",
        value=f"{stats.a_count}/{stats.b_count}/{stats.c_count}/{stats.d_count}",
    )
    embed.set_thumbnail(url=f"http://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
    await context.message.channel.send(embed=embed)
