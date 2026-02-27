
from .common import round_half_up
from slider import Beatmap

def fix_beatmap_decimal_values(beatmap: Beatmap) -> bool:
    """Round OD/AR/HP/CS values on a parsed beatmap in-place."""
    has_updates = False

    difficulty_attributes = (
        'overall_difficulty',
        'approach_rate',
        'hp_drain_rate',
        'circle_size'
    )

    for attribute_name in difficulty_attributes:
        value = getattr(beatmap, attribute_name)

        if float(value).is_integer():
            continue

        rounded_value = round_half_up(value)
        setattr(beatmap, attribute_name, rounded_value)
        has_updates = True

    return has_updates
