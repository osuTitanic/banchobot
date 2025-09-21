
from typing import Literal

Modes = {"standard": 0, "taiko": 1, "catch": 2, "mania": 3}
ModeType = Literal["standard", "taiko", "catch", "mania"]
RankingType = Literal["performance", "ppv1", "score", "total_score"]
StatusType = Literal["graveyard", "wip", "pending", "ranked", "approved", "qualified", "loved"]
