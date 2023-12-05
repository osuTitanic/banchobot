from app.common.database.objects import DBBeatmap, DBBeatmapset
from app.common.database.repositories import beatmapsets
from app.common.constants import DatabaseStatus
from app.objects import Context
from datetime import datetime
from ossapi import OssapiV1
from discord import Embed

import config
import utils
import app

@app.session.commands.register(['addset'], roles=['Admin'])
async def add_beatmapset(context: Context):
    """<set_id> - Add a beatmapset to the database"""

    if not context.args or not context.args[0].isnumeric():
        if not context.message.attachments:
            await context.message.channel.send(
                f'Invalid syntax: `!{context.command} <set_id>`',
                reference=context.message,
                mention_author=True
            )
            return

    async def add_set(set_id):
        if beatmapsets.fetch_one(set_id):
            return None, 'This beatmapset already exists!'

        api = OssapiV1(config.OSU_API_KEY)

        if not (maps := api.get_beatmaps(beatmapset_id=set_id)):
            return None, 'Could not find that beatmapset!'

        db_set = utils.add_beatmapset(set_id, maps)
        updates = list()
        
        # We need to get beatmapset from database to fix relationships
        with app.session.database.session as session:
            if (db_set := session.get(DBBeatmapset, set_id)) is not None:
                updates = utils.fix_beatmapset(db_set)

        return db_set, updates

    async with context.message.channel.typing():
        if context.message.attachments:
            if not context.message.attachments[0].content_type.startswith('text/plain'):
                await context.message.channel.send(
                    f'Attach a proper beatmap list.',
                    reference=context.message,
                    mention_author=True
                )
                return

            file = await context.message.attachments[0].read()
            
            added_count = 0
            updates_count = 0
            error = list()
            
            for set_id in file.decode().split('\n'):
                if not set_id:
                    break
                if not set_id.strip().isnumeric():
                    await context.message.channel.send(
                        'Attach a proper beatmap list.',
                        reference=context.message,
                        mention_author=True
                    )
                    return
                
                set_id = int(set_id.strip())
                db_set, updates = await add_set(set_id)
                
                if not db_set:
                    error.append(str(set_id))
                else:
                    added_count += 1
                    updates_count += len(updates)
            
            await context.message.channel.send(
                f'Added {added_count} sets. ({updates_count} edited, {len(error)} errored out.)',
                reference=context.message,
                mention_author=True
                )
            if error:
                await context.message.channel.send(
                f'These beatmap could not be added:\n```{" ".join(error)}```',
                reference=context.message,
                mention_author=True
                )
        else:
            set_id = int(context.args[0])
            db_set, updates = await add_set(set_id)
            
            if not db_set:
                await context.message.channel.send(
                    updates,
                    reference=context.message,
                    mention_author=True
                )
                return
            
            await context.message.channel.send(
                f'[Beatmapset was created. ({len(updates)} edited)](http://osu.{config.DOMAIN_NAME}/s/{db_set.id})',
                reference=context.message,
                mention_author=True
            )

@app.session.commands.register(['fixset'], roles=['Admin'])
async def fix_beatmapset(context: Context):
    """<set_id> - Fix the beatmap files for a beatmapset"""

    if not context.args or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <set_id>`',
            reference=context.message,
            mention_author=True
        )
        return

    set_id = int(context.args[0])

    async with context.message.channel.typing():
        with app.session.database.session as session:
            if not (beatmapset := session.get(DBBeatmapset, set_id)):
                await context.message.channel.send(
                    'This beatmapset does not exist!',
                    reference=context.message,
                    mention_author=True
                )
                return
            session.expunge(beatmapset)

            updates = fix_beatmapset(beatmapset)
            embed = Embed(title="Beatmap updates", description="Changes:\n")
        
            for updated_map in updates:
                embed.description += f"[{updated_map.version}](http://osu.{config.DOMAIN_NAME}/b/{updated_map.id})\n"
        
        await context.message.channel.send(
            embed=embed,
            reference=context.message,
            mention_author=True
        )


@app.session.commands.register(['modset'], roles=['BAT', 'Admin'])
async def change_beatmapset_status(context: Context):
    """<set_id> <status> - Modify a beatmapset status"""

    if context.message.attachments:
        if len(context.args) < 1 or not context.message.attachments[0].content_type.startswith('text/plain'):
            await context.message.channel.send(
                f'Invalid syntax: `!{context.command} <set_id> <status>`',
                reference=context.message,
                mention_author=True
            )
            return
    elif len(context.args) < 2 or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <set_id> <status>`',
            reference=context.message,
            mention_author=True
        )
        return

    index = 1 if not context.message.attachments else 0

    if context.args[index].lstrip('-+').isdigit():
        status = int(context.args[index])
        if status not in DatabaseStatus.values():
            statuses = {status.name:status.value for status in DatabaseStatus}
            statuses = "\t\n".join([f"{value}: {name}" for name, value in statuses.items()])
            await context.message.channel.send(
                f'Invalid status! Valid status: ```\n{statuses}```',
                reference=context.message,
                mention_author=True
            )
            return

    else:
        # Get valid statuses from enum
        statuses = {
            status.name.lower():status.value
            for status in DatabaseStatus
        }
        if context.args[index].lower() not in statuses:
            statuses = {status.name:status.value for status in DatabaseStatus}
            statuses = "\t\n".join([f"{value}: {name}" for name, value in statuses.items()])
            await context.message.channel.send(
                f'Invalid status! Valid status: ```\n{statuses}```',
                reference=context.message,
                mention_author=True
            )
            return
        status = statuses[context.args[index].lower()]

    def update_beatmapset(session, set_id: int, status: int):
        session.query(DBBeatmapset) \
            .filter(DBBeatmapset.id == set_id) \
            .update({
                'status': status,
                'last_update': datetime.now()
            })
        rows_changed = session.query(DBBeatmap) \
            .filter(DBBeatmap.set_id == set_id) \
            .update({
                'status': status,
                'last_update': datetime.now()
            })
        return rows_changed

    async with context.message.channel.typing():
        with app.session.database.session as session:
            if context.message.attachments:

                file = await context.message.attachments[0].read()
                rows_changed = 0
                            
                for set_id in file.decode().split('\n'):
                    if not set_id:
                        break
                    if not set_id.strip().isnumeric():
                        await context.message.channel.send(
                            'Attach a proper beatmap list.',
                            reference=context.message,
                            mention_author=True
                        )
                        return
                    set_id = int(set_id.strip())
                    rows_changed += update_beatmapset(session, set_id, status)
            else:
                set_id = int(context.args[0])
                rows_changed = update_beatmapset(session, set_id, status)
            
            session.commit()
        
        await context.message.channel.send(
            f'Changed {rows_changed} beatmaps.',
            reference=context.message,
            mention_author=True
        )
