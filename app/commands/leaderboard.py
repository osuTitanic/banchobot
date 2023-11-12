
from app.common.database.repositories import users
from app.common.cache.leaderboards import top_players
from app.common.constants import GameMode
from app.objects import Context

from discord import Embed
from discord import Color

import config
import app

@app.session.commands.register(["leaderboard", "lb"])
async def leaderboard(context: Context):
    """<std/taiko/ctb/mania> <pp/score> - Displays leaderboard"""
    if not (user := users.fetch_by_discord_id(context.message.author.id)):
        await context.message.channel.send("You don't have an account linked!")
        return

    mode = user.preferred_mode
    modes = {"std": 0, "taiko": 1, "ctb": 2, "mania": 3}
    modes_reversed = {0: "Standard", 1: "Taiko", 2: "Catch the beat", 3: "Mania"}
    type = "pp"

    if context.args:
        for arg in context.args:
            if arg in modes:
                mode = modes[arg]
            elif arg in ["pp", "score"]:
                type = arg
            else:
                await context.message.reply(
                    f"Wrong mode! Available modes: {', '.join(modes.keys())}"
                )
                return

    lb = top_players(
        mode=mode, range=10, type="performance" if type == "pp" else "rscore"
    )

    value_name = "pp" if type == "pp" else " ranked score"
    str = "```"
    position = 1
    for player_id, value in lb:
        player = users.fetch_by_id(player_id)
        str += f"#{position}. {player.name}: {value:,.0f}{value_name}\n"
        position += 1
    str += "```"

    mode_name = GameMode(mode).alias
    order_type = {'pp': 'performance', 'score': 'rscore'}[type]
    web_link = f"http://osu.{config.DOMAIN_NAME}/rankings/{order_type}/{mode_name}"

    await context.message.reply(
        embed=Embed(
            title=f"{modes_reversed[mode]} {type} leaderboard",
            url=web_link,
            description=str,
            color=Color.blue(),
        )
    )
