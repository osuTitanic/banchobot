from app.common.database.repositories import users, scores
from app.common.database.objects import DBStats
from app.common.constants import Mods
from app.objects import Context
from discord import Embed
from discord import Color

import config
import app


@app.session.commands.register(["lb", "leaderboard"])
async def leaderboard(context: Context):
    pass
