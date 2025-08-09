
from app.common.database.repositories import users
from app.common.cache import status
from app.objects import Context

import asyncio
import discord
import random
import string
import app

@app.session.commands.register(['link'])
async def create_account(context: Context):
    """<username> - Link your account to discord"""
    author = context.message.author # Hello
    
    if users.fetch_by_discord_id(author.id):
        await context.message.channel.send(
            'You already have an account linked to your discord profile.',
            reference=context.message,
            mention_author=True
        )
        return

    if not context.args:
        await context.message.channel.send(
            'Invalid syntax: `!link <username>`',
            reference=context.message,
            mention_author=True
        )
        return


    username = ' '.join(context.args[0:])

    if not (user := users.fetch_by_name_extended(username)):
        await context.message.channel.send(
            'This user was not found.',
            reference=context.message,
            mention_author=True
        )
        return

    if user.discord_id:
        await context.message.channel.send(
            'This user already linked their account to discord.',
            reference=context.message,
            mention_author=True
        )
        return

    if not status.exists(user.id):
        await context.message.channel.send(
            'Please log into the game and try again!',
            reference=context.message,
            mention_author=True
        )
        return

    app.session.logger.info(f'[{author}] -> Starting linking process...')

    code = ''.join(random.choices(string.ascii_lowercase, k=5))

    app.session.events.submit(
        'link',
        user_id=user.id,
        code=code
    )

    await context.message.channel.send(
        'Please enter the code that you received inside the game!',
        reference=context.message,
        mention_author=True
    )

    try:
        while True:
            msg: discord.Message = await app.session.bot.wait_for(
                'message',
                check=lambda msg: (msg.author.id == author.id),
                timeout=60
            )

            if msg.content != code:
                await msg.channel.send(
                    "The codes don't match, please try again!",
                    reference=msg,
                    mention_author=True
                )
                continue

            users.update(
                user.id,
                {'discord_id': msg.author.id}
            )

            app.session.logger.info(
                f'Account was linked to: {msg.author.name} ({msg.author.id})'
            )

            try:
                # Add "Member" role
                if type(context.message.channel) is discord.DMChannel:
                    guild = app.session.bot.guilds[0]
                    member = guild.get_member(context.message.author.id)

                    await member.add_roles(
                        discord.utils.get(guild.roles, name='Member')
                    )

                else:
                    await context.message.author.add_roles(
                        discord.utils.get(author.guild.roles, name='Member')
                    )
            except Exception as e:
                app.session.logger.warning(
                    f'[{author}] -> Failed to assign role: {e}',
                    exc_info=e
                )

            await msg.channel.send(
                "Successfully linked your account.",
                reference=msg,
                mention_author=True
            )
            break
    except asyncio.TimeoutError:
        app.session.logger.warning(
            'Registration was cancelled due to timeout.'
        )
        await context.message.channel.send(
            content='The account linking proccess was cancelled due to inactivity. '
                    'Please try again!'
        )
