
from __future__ import annotations
from typing import Tuple

from app.common.webhooks import Embed as WebhookEmbed, Image, Author
from app.common.database.repositories import beatmapsets, beatmaps
from app.common.constants import DatabaseStatus, Mods
from app.common.helpers import performance

from rosu_pp_py import Performance, Beatmap
from datetime import datetime, timedelta
from app.objects import Context
from discord import Embed
from ossapi import Ossapi

import app.common
import hashlib
import config
import utils
import app

async def add_set(set_id: int):
    with app.session.database.managed_session() as session:
        if beatmapsets.fetch_one(set_id, session):
            return None, 'This beatmapset already exists!'

        api = Ossapi(
            config.OSU_CLIENT_ID,
            config.OSU_CLIENT_SECRET
        )

        try:
            set = api.beatmapset(beatmapset_id=set_id)
            assert set
        except (AssertionError, ValueError):
            return None, 'Could not find that beatmapset!'

        db_set = utils.add_beatmapset(set_id, set, session)
        updates = list()

        if (db_set := beatmapsets.fetch_one(set_id, session)) is not None:
            updates = utils.fix_beatmapset(db_set, session)

    return db_set, updates

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
        errors = list()

        for set_id in file.decode().split('\n'):
            if not set_id:
                break

            if not set_id.strip().isnumeric():
                errors.append(set_id)
                continue

            set_id = int(set_id.strip())
            db_set, updates = await add_set(set_id)

            if not db_set:
                errors.append(str(set_id))
            else:
                added_count += 1
                updates_count += len(updates)

        await context.message.channel.send(
            f'Added {added_count} sets. ({updates_count} edited, {len(errors)} errored out.)',
            reference=context.message,
            mention_author=True
        )

        if errors:
            await context.message.channel.send(
                f'These beatmap could not be added:\n```{" ".join(errors)}```',
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

    with app.session.database.managed_session() as session:
        if not (beatmapset := beatmapsets.fetch_one(set_id, session=session)):
            await context.message.channel.send(
                'This beatmapset does not exist!',
                reference=context.message,
                mention_author=True
            )
            return

        updates = utils.fix_beatmapset(beatmapset, session)
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

    api = Ossapi(
        config.OSU_CLIENT_ID,
        config.OSU_CLIENT_SECRET
    )

    try:
        if is_set:
            set = api.beatmapset(beatmapset_id=id)
        else:
            set = api.beatmapset(beatmap_id=id)

        assert set
    except (AssertionError, ValueError):
        await context.message.channel.send(
            f'Beatmap not found.',
            reference=context.message,
            mention_author=True
        )
        return

    maps = set.beatmaps
    beatmapset = beatmapsets.fetch_one(maps[0].beatmapset_id)
    titanic_status = -2

    if beatmapset:
        titanic_status = beatmapset.status

    beatmap_embed = Embed(title=f"{set.artist} - {set.title} ({set.creator})")
    b_status_name = [status.name for status in DatabaseStatus if status.value == set.status.value][0]
    t_status_name = [status.name for status in DatabaseStatus if status.value == titanic_status][0]

    beatmapset_info = ""
    beatmapset_info += f"Created: {set.submitted_date.strftime('%Y/%m/%d')}\nLast Updated: {set.last_updated.strftime('%Y/%m/%d')}\n"
    beatmapset_info += f"BPM: {maps[0].bpm} Length: {timedelta(seconds=maps[0].total_length)}\n Status: {b_status_name} on Bancho | {t_status_name} on Titanic\n"

    beatmap_embed.add_field(
        name="Info",
        value=beatmapset_info,
        inline=False
    )

    for beatmap in sorted(maps, key=lambda x: x.difficulty_rating, reverse=True):
        suffix = ""

        if beatmap.mode != 0:
            suffix = f" ({beatmap.mode.name.lower()})"

        beatmap_info = f"Circles: {beatmap.count_circles} | Sliders: {beatmap.count_sliders} | Spinners: {beatmap.count_spinners} | Max Combo: {beatmap.max_combo}x\n"
        beatmap_info += f"Original stats:  AR: {beatmap.ar} | OD: {beatmap.accuracy} | HP: {beatmap.drain} | CS: {beatmap.cs}\n"
        beatmap_info += f"Adapted stats: AR: {round(beatmap.ar)}  | OD: {round(beatmap.accuracy)}  | HP: {round(beatmap.drain)}  | CS: {round(beatmap.cs)}\n"

        try:
            mods_vn = {'NM': 0, 'HR': Mods.HardRock, 'HDDT': Mods.Hidden+Mods.DoubleTime}
            mods_rx = {'RX': Mods.Relax, 'HDDTRX': Mods.Hidden+Mods.DoubleTime+Mods.Relax, 'HDDTHRRX': Mods.HardRock+Mods.Hidden+Mods.DoubleTime+Mods.Relax}
            pp_info = ""

            if (beatmap_file := app.session.storage.get_beatmap(beatmap.id)):
                bm = Beatmap(bytes=beatmap_file)
                bm.convert(performance.convert_mode(beatmap.mode))
                pp_info += "PP: "

                for combo_name, mod_value in mods_vn.items():
                    perf = Performance(mods=mod_value)
                    result = perf.calculate(bm)
                    pp_info += f"{combo_name}: {result.pp:.0f} | "

                pp_info = pp_info[:-2]

                if beatmap.mode.value != 3:
                    pp_info += "\nPP: "

                    for combo_name, mod_value in mods_rx.items():
                        perf = Performance(mods=mod_value)
                        result = perf.calculate(bm)
                        pp_info += f"{combo_name}: {result.pp:.0f} | "

                    pp_info = pp_info[:-2]

                beatmap_info += f"{pp_info}\n"
        except:
            app.session.logger.warning(f"Failed to calculate performance!", exc_info=True)

        beatmap_embed.add_field(
            name=f"{beatmap.difficulty_rating:.1f}* {beatmap.version}{suffix}",
            value=beatmap_info,
            inline=False
        )

    beatmap_embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{maps[0].beatmapset_id}/covers/cover@2x.jpg")
    await context.message.channel.send(embed=beatmap_embed)

# i am not even going to attempt to cleanup this mess
def parse_status(string: str) -> Tuple[int, str | None]:
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

    with app.session.database.managed_session() as session:
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
                        'last_update': datetime.now(),
                        'approved_at': datetime.now() if status > DatabaseStatus.Pending else None
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
        else:
            set_id = int(context.args[0])
            beatmapsets.update(
                set_id,
                updates={
                    'status': status,
                    'last_update': datetime.now(),
                    'approved_at': datetime.now() if status > DatabaseStatus.Pending else None
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
        is_valid_list = (
            len(context.args) >= 1 and
            context.message.attachments[0].content_type.startswith('text/plain')
        )

        if not is_valid_list:
            await context.message.channel.send(
                f'Invalid syntax: `!{context.command} <beatmap_id> <status>`',
                reference=context.message,
                mention_author=True
            )
            return

    else:
        has_valid_args = (
            len(context.args) >= 2 and
            context.args[0].isnumeric()
        )

        if not has_valid_args:
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

    with app.session.database.managed_session() as session:
        if not context.message.attachments:
            beatmap_id = int(context.args[0])
            rows_changed = beatmaps.update(
                beatmap_id,
                updates={'status': status, 'last_update': datetime.now()},
                session=session
            )
            post_beatmap_change(beatmap_id)
            session.commit()

        else:
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

    await context.message.channel.send(
        f'Changed {rows_changed} {"beatmap" if rows_changed == 1 else "beatmaps"}.',
        reference=context.message,
        mention_author=True
    )

def post_beatmapset_change(beatmapset_id: int) -> None:
    if not (beatmapset := beatmapsets.fetch_one(beatmapset_id)):
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

def post_beatmap_change(beatmap_id: int) -> None:
    if not (beatmap := beatmaps.fetch_by_id(beatmap_id)):
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
async def fix_beatmap_hashes(context: Context):
    """<beatmapset_id> - Update the hashes of a beatmapset"""
    if not context.args:
        await context.message.channel.send('Invalid syntax: `!fixhash <beatmapset_id>`')
        return

    if not context.args[0].isnumeric():
        await context.message.channel.send('Invalid syntax: `!fixhash <beatmapset_id>`')
        return

    beatmapset_id = int(context.args[0])

    with app.session.database.managed_session() as session:
        beatmapset = beatmapsets.fetch_one(
            beatmapset_id,
            session=session
        )

        if not beatmapset:
            await context.message.channel.send('Beatmapset was not found.')
            return

        for beatmap in beatmapset.beatmaps:
            custom_beatmap = app.session.storage.get_beatmap_internal(beatmap.id)

            if custom_beatmap:
                # We have a custom file for this beatmap
                beatmap_hash = hashlib.md5(custom_beatmap).hexdigest()

            else:
                response = app.session.requests.get(f'https://osu.direct/api/b/{beatmap.id}')
                response.raise_for_status()

                beatmap_hash = response.json()['FileMD5']

            beatmaps.update(
                beatmap.id,
                updates={'md5': beatmap_hash},
                session=session
            )

        await context.message.channel.send(
            f'Updated hashes for {len(beatmapset.beatmaps)} beatmaps.'
        )

@app.session.commands.register(['uploadbeatmap', 'uploadmap'], roles=['BAT', 'Admin'])
async def upload_beatmap_file(context: Context):
    """<beatmap_id> - Update the hashes of a beatmapset"""
    if not context.args:
        await context.message.channel.send('Invalid syntax: `!uploadbeatmap <beatmap_id>`')
        return

    if not context.args[0].isnumeric():
        await context.message.channel.send('Invalid syntax: `!uploadbeatmap <beatmap_id>`')
        return

    if not context.message.attachments:
        await context.message.channel.send('Attach a beatmap file.')
        return

    beatmap_id = int(context.args[0])

    with app.session.database.managed_session() as session:
        beatmap = beatmaps.fetch_by_id(beatmap_id, session=session)

        if not beatmap:
            await context.message.channel.send('Beatmap was not found.')
            return

        file = await context.message.attachments[0].read()

        app.session.storage.upload_beatmap_file(
            beatmap.id,
            file
        )

        beatmaps.update(
            beatmap.id,
            updates={'md5': hashlib.md5(file).hexdigest()},
            session=session
        )

    await context.message.channel.send(
        f'Uploaded beatmap file for "{beatmap.version}".'
    )
