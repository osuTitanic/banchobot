
from app.common.database.repositories import *
from app.common.cache import leaderboards
from app.objects import Context

import config
import app

@app.session.commands.register(['restrict', 'ban'], roles=['Admin'])
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

    reason = "No reason." if len(context.args) < 2 else " ".join(context.args[1:])

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
        # Let bancho handle restriction
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
            
@app.session.commands.register(['unrestrict', 'unban'], roles=['Admin'])
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
    
    # Restore scores
    try:
        scores.restore_hidden_scores(user.id)
        stats.restore(user.id)
    except Exception as e:
        app.session.logger.error(
            f'Failed to restore scores of player "{user.name}": {e}',
            exc_info=e
        )
        await context.message.reply("Failed to restore scores!")

    # Unrestrict HWID
    clients.update_all(user.id, {'banned': False})
    users.update(user.id, {'restricted': False, 'permissions': 5 if config.FREE_SUPPORTER else 1})
    
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
