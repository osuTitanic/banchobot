
from app.common.database.repositories import users
from app.objects import Context

import asyncio
import hashlib
import discord
import config
import bcrypt
import app

@app.session.commands.register(['register'])
async def create_account(context: Context):
    """Create an account"""
    author = context.message.author

    if users.fetch_by_discord_id(author.id):
        await context.message.channel.send(
            'You already have an account linked to your discord profile.',
            reference=context.message,
            mention_author=True
        )
        return

    app.session.logger.info(f'[{author}] -> Starting registration process...')

    if type(context.message.channel) is not discord.DMChannel:
        await context.message.channel.send(
            content='Please check your dms!',
            reference=context.message,
            mention_author=True
        )

    dm = await author.create_dm()
    await dm.send(
        'You are about to register an account on osuTitanic.\n'
        'Please enter a username!'
    )

    def check(msg: discord.Message):
        return (
            msg.author.id == author.id and
            isinstance(msg.channel, discord.DMChannel)
        )

    try:
        while True:
            msg: discord.Message = await app.session.bot.wait_for(
                'message',
                check=check,
                timeout=60
            )

            username = msg.content.strip()
            safe_name = username.lower() \
                                .replace(' ', '_')

            # TODO: Check and remove invalid characters

            # Check if user already exists
            if users.fetch_by_safe_name(safe_name):
                await dm.send('A user with that name already exists. Please try again!')
                continue
            else:
                break

        app.session.logger.info(
            f'[{author}] -> Selcted username "{username}"'
        )

        await dm.send(f'Your username will be "{username}".\n')
        await dm.send(
            'Please enter a password for you to log in!\n'
            '(Type "abort" to abort the registration)'
        )

        msg: discord.Message = await app.session.bot.wait_for(
            'message',
            check=check,
            timeout=60
        )

        password: str = msg.content

        if password.lower() == 'abort':
            app.session.logger.info(f'[{author}] -> Registration was cancelled')
            await dm.send('The registration was cancelled.')
            return

        async with dm.typing():
            hashed_password = bcrypt.hashpw(
                password=hashlib.md5(password.encode()) \
                                .hexdigest() \
                                .encode(),
                salt=bcrypt.gensalt()
            ).decode()

            app.session.logger.info(
                f'[{author}] -> Creating user...'
            )

            user = users.create(
                username=username,
                safe_name=safe_name,
                email='user@example.com', # TODO
                pw_bcrypt=hashed_password,
                country='XX',
                activated=True,
                discord_id=author.id,
                permissions=1 if not config.FREE_SUPPORTER else 5
            )

            if not user:
                app.session.logger.warning('Failed to register user.')
                await dm.send(
                    'Something went wrong during the registration. Please contact a developer!'
                )
                return

            app.session.logger.info(
                f'[{author}] -> Trying to get profile picture from discord...'
            )

            try:
                # Try to get profile picture
                r = app.session.requests.get(author.avatar.url)
                r.raise_for_status()

                app.session.storage.upload_avatar(
                    user.id,
                    r.content
                )
            except Exception as e:
                app.session.logger.warning(
                    'Failed to get profile picture from discord.',
                    exc_info=e
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
                    f'Failed to assign role: {e}',
                    exc_info=e
                )

        await dm.send(
            "Thank you! You can now try to log in.\n"
            "If something doesn't work, feel free to ping a developer or admin.\n"
            "Have fun playing on this server!"
        )

    except asyncio.TimeoutError:
        app.session.logger.warning(
            'Registration was cancelled due to timeout.'
        )
        await dm.send(
            content='The registration was cancelled due to inactivity.\n'
                    'Please try again!'
        )


