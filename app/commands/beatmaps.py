
from app.common.webhooks import Embed as WebhookEmbed, Image, Author

from app.common.database.repositories import beatmapsets, beatmaps
from app.common.database.objects import DBBeatmap, DBBeatmapset
from app.common.constants import DatabaseStatus, Mods

from titanic_pp_py import Calculator, Beatmap
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.objects import Context
from ossapi import OssapiV1
from discord import Embed

import app.common
import hashlib
import config
import utils
import app

@app.session.commands.register(['addset'], roles=['Admin', 'BAT'])
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
                    error.append(set_id)
                    continue

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
            
            post_beatmapset_change(set_id)
            
            await context.message.channel.send(
                f'[Beatmapset was created. ({len(updates)} edited)](http://osu.{config.DOMAIN_NAME}/s/{db_set.id})',
                reference=context.message,
                mention_author=True
            )

@app.session.commands.register(['fixset'], roles=['Admin', 'BAT'])
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

            updates = utils.fix_beatmapset(beatmapset)
            embed = Embed(title="Beatmap updates", description="Changes:\n")

            for updated_map in updates:
                embed.description += f"[{updated_map.version}](http://osu.{config.DOMAIN_NAME}/b/{updated_map.id})\n"

        await context.message.channel.send(
            embed=embed,
            reference=context.message,
            mention_author=True
        )

@app.session.commands.register(['beatmap_info'])
async def beatmap_info(context: Context):
    """<link> - Get information about a beatmap"""
    if not context.args:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <link>`',
            reference=context.message,
            mention_author=True
        )
        return
        
    link = context.args[0]
    is_set = "/beatmapsets/" in link or "/s/" in link
    id = 0
    
    for char in link:
        if char.isdigit():
            id = id * 10 + int(char) # funny
        elif id != 0:
            break
            
    if not id:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <link>`',
            reference=context.message,
            mention_author=True
        )
        return
        
    api = OssapiV1(config.OSU_API_KEY)
    
    if is_set:
        maps = api.get_beatmaps(beatmapset_id=id)
    else:
        map = api.get_beatmaps(beatmap_id=id)
        if not map:
            await context.message.channel.send(
                f'Beatmap not found.',
                reference=context.message,
                mention_author=True
            )
            return
            
        maps = api.get_beatmaps(beatmapset_id=map[0].beatmapset_id)

    if not maps:
        await context.message.channel.send(
            f'Beatmap not found.',
            reference=context.message,
            mention_author=True
        )
        return

    beatmapset = beatmapsets.fetch_one(maps[0].beatmapset_id)

    if not beatmapset:
        titanic_status = -2
    else:
        titanic_status = beatmapset.status

    beatmap_embed = Embed(title=f"{maps[0].artist} - {maps[0].title} ({maps[0].creator})")
    b_status_name = [status.name for status in DatabaseStatus if status.value == int(maps[0].approved)][0]
    t_status_name = [status.name for status in DatabaseStatus if status.value == titanic_status][0]

    beatmapset_info = ""
    beatmapset_info += f"Created: {maps[0].submit_date.strftime('%Y/%m/%d')}\nLast Updated: {maps[0].last_update.strftime('%Y/%m/%d')}\n"
    beatmapset_info += f"BPM: {maps[0].bpm} Length: {timedelta(seconds=maps[0].total_length)}\n Status: {b_status_name} on Bancho | {t_status_name} on Titanic\n"
    
    beatmap_embed.add_field(name="Info", value=beatmapset_info, inline=False)
    
    for beatmap in sorted(maps, key=lambda x: x.star_rating, reverse=True):
        suffix = ""
        
        if beatmap.mode != 0:
            suffix = f" ({['osu', 'taiko', 'catch', 'mania'][beatmap.mode]})"
            
        beatmap_info = f"Circles: {beatmap.count_hitcircles} | Sliders: {beatmap.count_sliders} | Spinners: {beatmap.count_spinners} | Max Combo: {beatmap.max_combo}x\n"
        beatmap_info += f"Original stats:  AR: {beatmap.approach_rate} | OD: {beatmap.overrall_difficulty} | HP: {beatmap.health} | CS: {beatmap.circle_size}\n"
        beatmap_info += f"Adapted stats: AR: {round(beatmap.approach_rate)}  | OD: {round(beatmap.overrall_difficulty)}  | HP: {round(beatmap.health)}  | CS: {round(beatmap.circle_size)}\n"
        
        try:
            mods_vn = {'NM': 0, 'HR': Mods.HardRock, 'HDDT': Mods.Hidden+Mods.DoubleTime}
            mods_rx = {'RX': Mods.Relax, 'HDDTRX': Mods.Hidden+Mods.DoubleTime+Mods.Relax, 'HDDTHRRX': Mods.HardRock+Mods.Hidden+Mods.DoubleTime+Mods.Relax}
            pp_info = ""
            
            if (beatmap_file := app.session.storage.get_beatmap(beatmap.beatmap_id)):
                bm = Beatmap(bytes=beatmap_file)
                pp_info += "PP: "
                
                for combo_name, mod_value in mods_vn.items():
                    calc = Calculator(mods=mod_value)
                    result = calc.performance(bm)
                    pp_info += f"{combo_name}: {result.pp:.0f} | "
                    
                pp_info = pp_info[:-2]
                
                if beatmap.mode != 3:
                    pp_info += "\nPP: "
                    
                    for combo_name, mod_value in mods_rx.items():
                        calc = Calculator(mods=mod_value)
                        result = calc.performance(bm)
                        pp_info += f"{combo_name}: {result.pp:.0f} | "
                        
                    pp_info = pp_info[:-2]
                beatmap_info += f"{pp_info}\n"
        except:
            app.session.logger.warning(f"Failed to calculate performance!", exc_info=True)
            
        beatmap_embed.add_field(name=f"{beatmap.star_rating:.1f}* {beatmap.version}{suffix}", value=beatmap_info, inline=False)
    beatmap_embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{maps[0].beatmapset_id}/covers/cover@2x.jpg")
    await context.message.channel.send(embed=beatmap_embed)

def parse_status(string):
    if string.lstrip('-+').isdigit():
        status = int(string)
        if status not in DatabaseStatus.values():
            statuses = {status.name:status.value for status in DatabaseStatus}
            statuses = "\t\n".join([f"{value}: {name}" for name, value in statuses.items()])
            return -10, f'Invalid status! Valid status: ```\n{statuses}```'
    else:
        # Get valid statuses from enum
        statuses = {
            status.name.lower():status.value
            for status in DatabaseStatus
        }
        if string.lower() not in statuses:
            statuses = {status.name:status.value for status in DatabaseStatus}
            statuses = "\t\n".join([f"{value}: {name}" for name, value in statuses.items()])
            return -10, f'Invalid status! Valid status: ```\n{statuses}```'
        status = statuses[string.lower()]
    return status, None

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

    status, err = parse_status(context.args[index])
    if err:
        await context.message.channel.send(
            err,
            reference=context.message,
            mention_author=True
        )
        return

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
                    beatmapsets.update(
                        set_id,
                        updates={
                            'status': status,
                            'last_update': datetime.now()
                        },
                        session=session
                    )
                    rows_changed += beatmaps.update_by_set_id(
                        set_id,
                        updates={
                            'status': status,
                            'last_update': datetime.now()
                        },
                        session=session
                    )
                session.commit()
            else:
                set_id = int(context.args[0])
                beatmapsets.update(
                    set_id,
                    updates={
                        'status': status,
                        'last_update': datetime.now()
                    },
                    session=session
                )
                rows_changed = beatmaps.update_by_set_id(
                    set_id,
                    updates={
                        'status': status,
                        'last_update': datetime.now()
                    },
                    session=session
                )
                post_beatmapset_change(set_id)
                session.commit()

        await context.message.channel.send(
            f'Changed {rows_changed} {"beatmap" if rows_changed == 1 else "beatmaps"}.',
            reference=context.message,
            mention_author=True
        )


@app.session.commands.register(['moddiff'], roles=['BAT', 'Admin'])
async def change_beatmap_status(context: Context):
    """<beatmap_id> <status> - Modify a beatmap status"""

    if context.message.attachments:
        if len(context.args) < 1 or not context.message.attachments[0].content_type.startswith('text/plain'):
            await context.message.channel.send(
                f'Invalid syntax: `!{context.command} <beatmap_id> <status>`',
                reference=context.message,
                mention_author=True
            )
            return

    elif len(context.args) < 2 or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <beatmap_id> <status>`',
            reference=context.message,
            mention_author=True
        )
        return

    index = 1 if not context.message.attachments else 0

    status, err = parse_status(context.args[index])
    if err:
        await context.message.channel.send(
            err,
            reference=context.message,
            mention_author=True
        )
        return

    async with context.message.channel.typing():
        with app.session.database.session as session:
            if context.message.attachments:

                file = await context.message.attachments[0].read()
                rows_changed = 0

                for beatmap_id in file.decode().split('\n'):
                    if not beatmap_id:
                        break

                    if not beatmap_id.strip().isnumeric():
                        await context.message.channel.send(
                            'Attach a proper beatmap list.',
                            reference=context.message,
                            mention_author=True
                        )
                        return

                    beatmap_id = int(beatmap_id.strip())
                    rows_changed += beatmaps.update(
                        beatmap_id,
                        updates={'status': status, 'last_update': datetime.now()},
                        session=session
                    )

                session.commit()

            else:
                beatmap_id = int(context.args[0])
                rows_changed = beatmaps.update(
                    beatmap_id,
                    updates={'status': status, 'last_update': datetime.now()},
                    session=session
                )
                post_beatmap_change(beatmap_id)
                session.commit()

        await context.message.channel.send(
            f'Changed {rows_changed} {"beatmap" if rows_changed == 1 else "beatmaps"}.',
            reference=context.message,
            mention_author=True
        )

def post_beatmapset_change(beatmapset_id: int):
    beatmapset = beatmapsets.fetch_one(beatmapset_id)
    if not beatmapset:
        return
    status_name = [status.name for status in DatabaseStatus if status.value == beatmapset.status][0]
    embed = WebhookEmbed(title=f'Status change: {beatmapset.title}')
    embed.image = Image(url=f'https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover.jpg')
    embed.author = Author(name="New beatmapset update!")
    embed.add_field(name="Artist", value=beatmapset.artist, inline=True)
    embed.add_field(name="Creator", value=beatmapset.creator, inline=True)
    embed.add_field(name="New status", value=status_name, inline=True)
    embed.add_field(name="Bancho url", value=f"https://osu.ppy.sh/s/{beatmapset.id}", inline=True)
    embed.add_field(name="Titanic url", value=f"https://osu.{config.DOMAIN_NAME}/s/{beatmapset.id}", inline=True)
    app.common.officer.event(embeds=[embed])

def post_beatmap_change(beatmap_id: int):
    beatmap = beatmaps.fetch_by_id(beatmap_id)
    if not beatmap:
        return
    beatmapset = beatmap.beatmapset
    status_name = [status.name for status in DatabaseStatus if status.value == beatmap.status][0]
    embed = WebhookEmbed(title=f'Status change: {beatmapset.title} ({beatmap.version})')
    embed.image = Image(url=f'https://assets.ppy.sh/beatmaps/{beatmapset.id}/covers/cover.jpg')
    embed.author = Author(name="New beatmap update!")
    embed.add_field(name="Artist", value=beatmapset.artist, inline=True)
    embed.add_field(name="Creator", value=beatmapset.creator, inline=True)
    embed.add_field(name="New status", value=status_name, inline=True)
    embed.add_field(name="Bancho url", value=f"https://osu.ppy.sh/b/{beatmap.id}", inline=True)
    embed.add_field(name="Titanic url", value=f"https://osu.{config.DOMAIN_NAME}/b/{beatmap.id}", inline=True)
    app.common.officer.event(embeds=[embed])

@app.session.commands.register(['fixhash'], roles=['BAT', 'Admin'])
async def fix_beatmap_hashes(ctx: Context):
    """<beatmap_id> - Update the hashes of a beatmapset"""
    if not ctx.args:
        await ctx.send('Invalid syntax: `!fixhash <beatmapset_id>`')
        return

    if not ctx.args[0].isnumeric():
        await ctx.send('Invalid syntax: `!fixhash <beatmapset_id>`')
        return

    beatmapset_id = int(ctx.args[0])

    async with ctx.message.channel.typing():
        with app.session.database.session as session:
            beatmapset = beatmapsets.fetch_one(
                beatmapset_id,
                session=session
            )

            if not beatmapset:
                await ctx.send('Beatmapset was not found.')
                return

            for beatmap in beatmapset.beatmaps:
                custom_beatmap = app.session.storage.get_beatmap_internal(beatmap.id)

                if custom_beatmap:
                    # We have a custom file for this beatmap
                    beatmap_hash = hashlib.md5(custom_beatmap).hexdigest()

                else:
                    response = app.session.requests.get(f'https://api.osu.direct/b/{beatmap.id}')
                    response.raise_for_status()

                    beatmap_hash = response.json()['FileMD5']

                beatmaps.update(
                    beatmap.id,
                    updates={'md5': beatmap_hash},
                    session=session
                )

            await ctx.message.channel.send(
                f'Updated hashes for {len(beatmapset.beatmaps)} beatmaps.'
            )
