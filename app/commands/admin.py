from app.common.database.repositories import users
from app.common.database.objects import DBUser
from app.objects import Context

import app

@app.session.commands.register(['restrict', 'unrestrict'], roles=['Admin'])
async def restrict(context: Context):
    """<user_id> - (Un)Restrict user"""
    if not context.args or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <user_id>`',
            reference=context.message,
            mention_author=True
        )
        return
    
    user_id = int(context.args[0])
    
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
            with app.session.database.managed_session() as session:
                session.get(DBUser, user_id).restricted = True
                session.commit()

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
            with app.session.database.managed_session() as session:
                session.get(DBUser, user_id).restricted = False
                session.commit()

            await context.message.channel.send(
                f'User unrestricted.',
                reference=context.message,
                mention_author=True
            )
            