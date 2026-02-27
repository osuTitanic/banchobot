
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.database.repositories import wrapper
from app.common.database.repositories import *
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from slider import Beatmap
import app

def parse_beatmap(content: bytes, beatmap_id: int) -> Beatmap | None:
    try:
        decoded_content = content.decode("utf-8-sig")
        return Beatmap.parse(decoded_content)
    except Exception as error:
        app.session.logger.warning(
            f"Invalid beatmap file for '{beatmap_id}': {error}",
            exc_info=True
        )
        return None

def pack_beatmap(beatmap: Beatmap) -> bytes:
    return beatmap.pack().encode("utf-8")

def round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))

@wrapper.session_wrapper
def delete_beatmapset(beatmapset: DBBeatmapset, session: Session = ...) -> None:
    app.session.storage.remove_osz2(beatmapset.id)
    app.session.storage.remove_osz(beatmapset.id)
    app.session.storage.remove_background(beatmapset.id)
    app.session.storage.remove_mp3(beatmapset.id)

    for beatmap in beatmapset.beatmaps:
        app.session.storage.remove_beatmap_file(beatmap.id)
    
    # Delete all related data
    for beatmap in beatmapset.beatmaps:
        collaborations.delete_requests_by_beatmap(beatmap.id, session=session)
        collaborations.delete_by_beatmap(beatmap.id, session=session)

    modding.delete_by_set_id(beatmapset.id, session=session)
    ratings.delete_by_set_id(beatmapset.id, session=session)
    plays.delete_by_set_id(beatmapset.id, session=session)
    nominations.delete_all(beatmapset.id, session=session)
    favourites.delete_all(beatmapset.id, session=session)
    beatmaps.delete_by_set_id(beatmapset.id, session=session)
    beatmapsets.delete_by_id(beatmapset.id, session=session)

@wrapper.session_wrapper
def delete_beatmap(beatmap: DBBeatmap, session: Session = ...) -> None:
    app.session.storage.remove_beatmap_file(beatmap.id)

    collaborations.delete_requests_by_beatmap(beatmap.id, session=session)
    collaborations.delete_by_beatmap(beatmap.id, session=session)
    ratings.delete_by_beatmap_hash(beatmap.md5, session=session)
    plays.delete_by_beatmap_id(beatmap.id, session=session)
    beatmaps.delete_by_id(beatmap.id, session=session)
