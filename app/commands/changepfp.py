
from app.common.database.repositories import users
from app.objects import Context

import app

@app.session.commands.register(['changepfp'])
async def create_account(context: Context):
    """Change profile picture"""
    author = context.message.author

    if (user := users.fetch_by_discord_id(author.id)) is None:
        await context.message.channel.send(
            'You don\'t have an account linked!',
            reference=context.message,
            mention_author=True
        )
        return

    if not context.message.attachments or not context.message.attachments[0].content_type.startswith("image"):
        await context.message.channel.send(
            'Please attach an image!',
            reference=context.message,
            mention_author=True
        )
        return

    try:
        if context.message.attachments[0].size > 1250**2: # Approx 1.5mb
            await context.message.channel.send(
                'Image exceed the 1.5mb limit!',
                reference=context.message,
                mention_author=True
            )
            return

        if context.message.attachments[0].height > 5000:
            await context.message.channel.send(
                'Image exceed the height limit!',
                reference=context.message,
                mention_author=True
            )
            return

        if context.message.attachments[0].width > 5000:
            await context.message.channel.send(
                'Image exceed the width limit!',
                reference=context.message,
                mention_author=True
            )
            return

        r = app.session.requests.get(context.message.attachments[0].url)
        r.raise_for_status()

        app.session.storage.upload_avatar(
            user.id,
            r.content
        )
        await context.message.channel.send(
            'Profile picture changed.',
            reference=context.message,
            mention_author=True
        )
    except Exception as e:
        await context.message.channel.send(
            'An error occurred.',
            reference=context.message,
            mention_author=True
        )
        app.session.logger.warning(
            f'[{author}] -> Failed to get profile picture from discord.',
            exc_info=e
        )
