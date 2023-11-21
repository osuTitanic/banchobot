from app.common.database.repositories import users, names
from app.objects import Context

import app

@app.session.commands.register(['restrict'], roles=['Admin'])
async def restrict(context: Context):
    """<user_id> <reason> - Restrict user"""
    if not context.args:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id/mention> <reason>`',
            reference=context.message,
            mention_author=True
        )
        return
    
    if context.args[0].isnumeric():
        # Get internal user id
        discord_id = None
        user = users.fetch_by_id(int(context.args[0]))

    elif context.args[0].startswith("<@"):
        # Get discord id
        discord_id = int(context.args[0][2:-1])
        user = users.fetch_by_discord_id(discord_id)

    else:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id/mention> <reason>`',
            reference=context.message,
            mention_author=True
        )
        return

    reason = "No reason." if len(context.args) < 3 else " ".join(context.args[2:])

    if not user:
        await context.message.channel.send(
            f'User not found!',
            reference=context.message,
            mention_author=True
        )
        return

    if user.restricted:
        await context.message.channel.send(
            f'User is already restricted!',
            reference=context.message,
            mention_author=True
        )
    else:
        users.update(user.id, {'restricted': True})
        app.session.events.submit(
            'restrict',
            user_id=user.id,
            reason=reason
        )
        await context.message.channel.send(
            f'User restricted.',
            reference=context.message,
            mention_author=True
        )
            

@app.session.commands.register(['unrestrict'], roles=['Admin'])
async def unrestrict(context: Context):
    """<user_id> - Unrestrict user"""
    if not context.args:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id/mention>`',
            reference=context.message,
            mention_author=True
        )
        return
    
    if context.args[0].isnumeric():
        # Get internal user id
        discord_id = None
        user = users.fetch_by_id(int(context.args[0]))

    elif context.args[0].startswith("<@"):
        # Get discord id
        discord_id = int(context.args[0][2:-1])
        user = users.fetch_by_discord_id(discord_id)

    else:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id/mention> <reason>`',
            reference=context.message,
            mention_author=True
        )
        return

    if not user:
        await context.message.channel.send(
            f'User not found!',
            reference=context.message,
            mention_author=True
        )
        return

    if not user.restricted:
        await context.message.channel.send(
            f'User is already unrestricted!',
            reference=context.message,
            mention_author=True
        )
        return

    users.update(user.id, {'restricted': False})
    await context.message.channel.send(
        f'User unrestricted.',
        reference=context.message,
        mention_author=True
    )

@app.session.commands.register(['rename'], roles=['Admin'])
async def rename(context: Context):
    """<user_id> <new_name> - Rename user"""
    if len(context.args) < 2:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id> <new_name>`',
            reference=context.message,
            mention_author=True
        )
        return

    username = " ".join(context.args[1:])
    
    if context.args[0].isnumeric():
        # Get internal user id
        discord_id = None
        user = users.fetch_by_id(int(context.args[0]))

    elif context.args[0].startswith("<@"):
        # Get discord id
        discord_id = int(context.args[0][2:-1])
        user = users.fetch_by_discord_id(discord_id)

    else:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id/mention> <new_name>`',
            reference=context.message,
            mention_author=True
        )
        return

    if not user:
        await context.message.channel.send(
            'User not found!',
            reference=context.message,
            mention_author=True
        )
        return

    names.create(user.id, user.name)
    users.update(user.id, {'name': username})
    await context.message.channel.send(
        'User renamed.',
        reference=context.message,
        mention_author=True
    )