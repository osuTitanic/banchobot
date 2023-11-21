from app.common.database.repositories import users
from app.common.database.objects import DBUser
from app.objects import Context

import app

@app.session.commands.register(['restrict', 'unrestrict'], roles=['Admin'])
async def restrict(context: Context):
    """<user_id> <reason> - (Un)Restrict user"""
    if not context.args or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id> <reason>`',
            reference=context.message,
            mention_author=True
        )
        return
    
    user_id = int(context.args[0])
    reason = "No reason." if len(context.args) < 2 else " ".join(context.args[1:])

    if (user := users.fetch_by_id(user_id)) is None:
        await context.message.channel.send(
            f'User not found!',
            reference=context.message,
            mention_author=True
        )
        return

    if context.command == "restrict":
        if user.restricted:
            await context.message.channel.send(
                f'User is already restricted!',
                reference=context.message,
                mention_author=True
            )
        else:
            users.update(user_id, {'restricted': True})
            app.session.events.submit(
                'restrict',
                user_id=user_id,
                reason=reason
            )
            await context.message.channel.send(
                f'User restricted.',
                reference=context.message,
                mention_author=True
            )
    else:
        if not user.restricted:
            await context.message.channel.send(
                f'User is already unrestricted!',
                reference=context.message,
                mention_author=True
            )
        else:
            users.update(user_id, {'restricted': False})
            await context.message.channel.send(
                f'User unrestricted.',
                reference=context.message,
                mention_author=True
            )

@app.session.commands.register(['rename'], roles=['Admin'])
async def rename(context: Context):
    """<user_id> <new_name> - rename user"""
    if len(context.args) < 2 or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id> <new_name>`',
            reference=context.message,
            mention_author=True
        )
        return

    user_id = int(context.args[0])
    username = " ".join(context.args[1:])
    
    if users.fetch_by_id(user_id):
        users.update(user_id, {'name': username})
        await context.message.channel.send(
            'User renamed.',
            reference=context.message,
            mention_author=True
        )
    else:
        await context.message.channel.send(
            'User not found!',
            reference=context.message,
            mention_author=True
        )