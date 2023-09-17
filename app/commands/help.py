
from app.objects import Context
from discord import Embed
from discord import Color

import config
import app

@app.session.commands.register(['help', 'h'])
async def help(context: Context):
    """Displays this message"""

    embed = Embed(
        title='Usage',
        url='https://pbs.twimg.com/media/Dqnn54dVYAAVuki.jpg',
        color=Color.blue()
    )

    for command in app.session.commands.commands:
        if not command.has_permission(context.message.author):
            continue

        embed.add_field(
            name=f'{config.BOT_PREFIX}{command.triggers[0]}',
            value=command.function.__doc__
        )

    await context.message.channel.send(
        embed=embed,
        reference=context.message,
        mention_author=True
    )
