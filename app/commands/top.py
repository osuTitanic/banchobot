from app.common.database.repositories import users, scores
from app.common.constants import Mods
from app.objects import Context
from discord import Embed
from discord import Color
import config
import app


@app.session.commands.register(["top"])
async def top(context: Context):
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

    user_scores = scores.fetch_top_scores(user_id=user.id, mode=mode)[:10]
    if not user_scores:
        await context.message.reply(f"No scores found for user {user.name}.")
        return

    str_builder = ""
    position = 1

    for score in user_scores:
        rank = score.grade
        max_combo = score.max_combo
        accuracy = score.acc
        n300 = score.n300
        n100 = score.n100
        n50 = score.n50
        nmiss = score.nMiss
        pp = score.pp
        mods = Mods(score.mods).short
        beatmap_title = (
            f"{score.beatmap.beatmapset.title} [{score.beatmap.version}] +{mods}"
        )
        str_builder += f"{position}. {beatmap_title}\n"
        str_builder += f"   {rank} {max_combo}/{score.beatmap.max_combo} {accuracy*100:.2f}% [{n300}/{n100}/{n50}/{nmiss}] {pp:.2f}pp\n"
        position += 1

    embed = Embed(
        title=f"Top plays for {user.name}",
        url="https://pbs.twimg.com/media/Dqnn54dVYAAVuki.jpg",
        color=Color.blue(),
    )

    embed.set_thumbnail(url=f"https://osu.{config.DOMAIN_NAME}/a/{user.id}?h=50")
    embed.description = str_builder
    await context.message.channel.send(embed=embed)
