
from datetime import timedelta
from slider import Beatmap

def fix_beatmap_lead_in(beatmap: Beatmap, minimum_leadin: int = 1500) -> bool:
    """Set minimum audio lead-in on a parsed beatmap in-place."""
    current_leadin_value = int(beatmap.audio_lead_in.total_seconds() * 1000)

    if current_leadin_value >= minimum_leadin:
        return False

    beatmap.audio_lead_in = timedelta(milliseconds=minimum_leadin)
    return True
