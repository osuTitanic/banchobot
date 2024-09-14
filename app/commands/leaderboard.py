
from app.common.database.repositories import users
from app.common.cache import leaderboards
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

    modes_reversed = {0: "Standard", 1: "Taiko", 2: "Catch The Beat", 3: "Mania"}
    modes = {"std": 0, "taiko": 1, "ctb": 2, "mania": 3}
    types = ("pp", "score", "total_score", "ppv1")

    mode = user.preferred_mode
    type = "pp"

    for arg in context.args:
        if arg in modes:
            mode = modes[arg]
        elif arg in types:
            type = arg
        else:
            await context.message.reply(
                f"Wrong mode! Available modes: {', '.join(modes.keys())}"
            )
            return

    order_type = {'pp': 'performance', 'score': 'rscore', 'total_score': 'tscore', 'ppv1': 'ppv1'}[type]
    value_name = {'pp': 'pp', 'score': '', 'total_score': '', 'ppv1': 'pp'}[type]

    lb = leaderboards.top_players(
        mode=mode,
        range=10,
        type=order_type
    )

    str = "```"
    position = 1
    
    for player_id, value in lb:
        player = users.fetch_by_id(player_id)
        str += f"#{position}. {player.name}: {value:,.0f}{value_name}\n"
        position += 1
    
    str += "```"

    mode_name = GameMode(mode).alias
    web_link = f"http://osu.{config.DOMAIN_NAME}/rankings/{order_type}/{mode_name}"

    await context.message.reply(
        embed=Embed(
            title=f"{modes_reversed[mode]} {value_name} leaderboard",
            url=web_link,
            description=str,
            color=Color.blue(),
        )
    )
