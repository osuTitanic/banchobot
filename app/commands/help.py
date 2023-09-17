
from app.objects import Context

import app

@app.session.commands.register(['help', 'h'])
async def help(context: Context):
    ...
