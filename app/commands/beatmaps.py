
from app.common.database.repositories import beatmapsets, beatmaps
from app.objects import Context
from ossapi import OssapiV1

import hashlib
import config
import utils
import app

@app.session.commands.register(['addset'], roles=['Admin'])
async def add_beatmapset(context: Context):
    """<set_id> - Add a beatmapset to the database"""

    if not context.args or not context.args[0].isnumeric():
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <set_id>`',
            reference=context.message,
            mention_author=True
        )
        return

    set_id = int(context.args[0])

    async with context.message.channel.typing():
        if beatmapsets.fetch_one(set_id):
            await context.message.channel.send(
                'This beatmapset already exists!',
                reference=context.message,
                mention_author=True
            )
            return

        api = OssapiV1(config.OSU_API_KEY)

        if not (maps := api.get_beatmaps(beatmapset_id=set_id)):
            await context.message.channel.send(
                'Could not find that beatmapset!',
                reference=context.message,
                mention_author=True
            )
            return

        if (response := app.session.storage.api.osz(set_id, no_video=False)):
            filesize = int(response.headers.get('Content-Length', default=0))
        else:
            filesize = 0

        if maps[0].video:
            if (response := app.session.storage.api.osz(set_id, no_video=True)):
                filesize_novideo = int(response.headers.get('Content-Length', default=0))
            else:
                filesize_novideo = 0
        else:
            filesize_novideo = 0


        db_set = beatmapsets.create(
            maps[0].beatmapset_id,
            maps[0].title,
            maps[0].artist,
            maps[0].creator,
            maps[0].source,
            maps[0].tags,
            maps[0].approved,
            maps[0].video,
            maps[0].storyboard,
            maps[0].submit_date,
            maps[0].approved_date,
            maps[0].last_update,
            maps[0].language_id,
            maps[0].genre_id,
            osz_filesize=filesize,
            osz_filesize_novideo=filesize_novideo
        )

        for beatmap in maps:
            beatmaps.create(
                beatmap.beatmap_id,
                beatmap.beatmapset_id,
                beatmap.mode,
                beatmap.beatmap_hash,
                beatmap.approved,
                beatmap.version,
                utils.get_beatmap_filename(beatmap.beatmap_id),
                beatmap.submit_date,
                beatmap.last_update,
                beatmap.total_length,
                beatmap.max_combo,
                beatmap.bpm,
                beatmap.circle_size,
                beatmap.approach_rate,
                beatmap.overrall_difficulty,
                beatmap.health,
                beatmap.star_rating
            )

        await context.message.channel.send(
            f'[Beatmapset was created.](http://osu.{config.DOMAIN_NAME}/s/{db_set.id})',
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
        if not (beatmapset := beatmapsets.fetch_one(set_id)):
            await context.message.channel.send(
                'This beatmapset does not exist!',
                reference=context.message,
                mention_author=True
            )
            return

        for beatmap in beatmapset.beatmaps:
            beatmap_file = app.session.storage.get_beatmap(beatmap.id)
            beatmap_dict = utils.parse_beatmap_file(beatmap_file.decode())
            beatmap_updates = {}

            difficulty_attributes = {
                'OverallDifficulty': 'od',
                'ApproachRate': 'ar',
                'HPDrainRate': 'hp',
                'CircleSize': 'cs'
            }

            for key, short_key in difficulty_attributes.items():
                if key not in beatmap_dict['Difficulty']:
                    continue

                value = beatmap_dict['Difficulty'][key]

                if isinstance(value, int):
                    continue

                # Update value
                beatmap_updates[short_key] = round(value) # Database
                beatmap_dict['Difficulty'][key] = round(value) # File

            if not beatmap_updates:
                continue

            # Get new file
            content = utils.get_beatmap_file(beatmap_dict)

            # Upload to storage
            app.session.storage.upload_beatmap_file(beatmap.id, content)

            # Update beatmap hash
            beatmap_hash = hashlib.md5(content).hexdigest()
            beatmap_updates['md5'] = beatmap_hash

            # Update database
            beatmaps.update(beatmap.id, beatmap_updates)

            await context.message.channel.send(
                f'Updated "[{beatmap.version}](http://osu.{config.DOMAIN_NAME}/b/{beatmap.id})"'
            )

        await context.message.channel.send(
            'Done.',
            reference=context.message,
            mention_author=True
        )
