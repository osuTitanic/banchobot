
from titanic_pp_py import Calculator, Beatmap
from app.common.constants import Mods
from app.objects import Context

import app

@app.session.commands.register(["simulate", "pp"])
async def simulate(context: Context):
    """Simulate pp for a beatmap"""
    possible_args = ('id', 'mods', 'mode', 'combo', 'n300', 'n100', 'n50', 'geki', 'katu', 'miss')
    msg = context.message.content.split(" ")[1:]
    args = {}

    if len(msg) % 2 != 0:
        await context.message.reply(f"Wrong arguments! \nList of available arguments: {', '.join(possible_args)}")
        return

    for x in range(0, len(msg), 2):
        if not msg[x].startswith("-"):
            await context.message.reply(f"Arguments should start with \"-\"!")
            return

        if msg[x][1:] not in possible_args:
            await context.message.reply(f"Unknown argument {msg[x]}! \nList of available arguments: {', '.join(possible_args)}")
            return

        if msg[x][1:] == "mods":
            args['mods'] = Mods.from_string(msg[x+1])

        else:
            if not msg[x+1].isnumeric():
                await context.message.reply(f"Arguments must be numeric!")
                return

            args[msg[x][1:]] = int(msg[x+1])

    if not 'id' in args:
        await context.message.reply(f"Provide beatmap id!")
        return

    if not (beatmap_file := app.session.storage.get_beatmap(args['id'])):
        await context.message.reply(f"Can't find beatmap!")
        return

    calc = Calculator(mode=args['mode'] if 'mode' in args else 0)

    if 'mods' in args:
        calc.set_mods(args['mods'])
    if 'combo' in args:
        calc.set_combo(args['combo'])
    if 'n300' in args:
        calc.set_n300(args['n300'])
    if 'n100' in args:
        calc.set_n100(args['n100'])
    if 'n50' in args:
        calc.set_n50(args['n50'])
    if 'katu' in args:
        calc.set_n_katu(args['katu'])
    if 'geki' in args:
        calc.set_n_geki(args['geki'])
    if 'miss' in args:
        calc.set_n_misses(args['miss'])
        
    bm = Beatmap(bytes=beatmap_file)
    
    result = calc.performance(bm)
    await context.message.reply(f"PP: {result.pp:.2f}")
