
from app.common.database.repositories import beatmapsets, beatmaps
from app.objects import Context
from ossapi import OssapiV1

import config
import utils
import app

@app.session.commands.register(['addset'], roles=['Admin'])
async def add_beatmapset(context: Context):
    """<set_id> - Add a beatmapset to the database"""

    if not context.args:
        await context.message.channel.send(
            f'Invalid syntax: `!{context.command} <set_id>`',
            reference=context.message,
            mention_author=True
        )
        return

    if not context.args[0].isnumeric():
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


        beatmapsets.create(
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
            'Beatmapset was created.',
            reference=context.message,
            mention_author=True
        )
