from app.common.database.repositories import users, scores
from app.common.database.objects import DBStats
from app.common.constants import Mods
from app.objects import Context
from discord import Embed
from discord import Color

import config
import app


@app.session.commands.register(["stats"])
async def stats(context: Context):
    """<std/taiko/ctb/mania> - Displays your statistics"""
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

    stats: DBStats = user.stats[mode]

    embed = Embed(
        title=f"Statistics for {user.name} (#{stats.rank})",
        url="https://pbs.twimg.com/media/Dqnn54dVYAAVuki.jpg",
        color=Color.blue(),
    )

    embed.add_field(name="Ranked score", value=f"{stats.rscore:,}")
    embed.add_field(name="Total score", value=f"{stats.tscore:,}")
    embed.add_field(name="Total hits", value=f"{stats.total_hits:,}")
    embed.add_field(name="Play count", value=f"{stats.playcount:,}")
    embed.add_field(name="Play time", value=f"{stats.playtime/60/60:,.2f}h")
    embed.add_field(name="Replay views", value=f"{stats.replay_views:,}")
    embed.add_field(name="Accuracy", value=f"{stats.acc*100:.2f}%")
    embed.add_field(name="Max combo", value=f"{stats.max_combo:,}")
    embed.add_field(name="Performance points", value=f"{stats.pp:.0f}pp")
    embed.add_field(name="SS/SS+", value=f"{stats.x_count}/{stats.xh_count}")
    embed.add_field(name="S/S+", value=f"{stats.s_count}/{stats.sh_count}")
    embed.add_field(
        name="A/B/C/D",
        value=f"{stats.a_count}/{stats.b_count}/{stats.c_count}/{stats.d_count}",
    )
    embed.set_thumbnail(url=f"https://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
    await context.message.channel.send(embed=embed)
