
from rosu_pp_py import Performance, Beatmap
from app.common.helpers import performance
from app.common.constants import Mods
from app.objects import Context

import app

@app.session.commands.register(["simulate", "pp"])
async def simulate(context: Context):
    """Simulate pp for a beatmap"""
    msg = context.message.content.split(" ")[1:]
    args = {}

    possible_args = (
        'id', 'acc', 'mods', 'mode',
        'combo', 'n300', 'n100',
        'n50', 'geki', 'katu', 'miss'
    )

    if len(msg) % 2 != 0:
        await context.message.reply(f"Wrong arguments! \nList of available arguments: {', '.join(possible_args)}")
        return

    for index in range(0, len(msg), 2):
        if not msg[index].startswith("-"):
            await context.message.reply(f"Arguments should start with \"-\"!")
            return

        argument_name = msg[index][1:].strip('-')

        if argument_name not in possible_args:
            await context.message.reply(f"Unknown argument {msg[index]}! \nList of available arguments: {', '.join(possible_args)}")
            return

        if argument_name == "mods":
            args['mods'] = Mods.from_string(msg[index+1]).value
            continue

        elif argument_name == "acc":
            try:
                acc = msg[index+1].removesuffix("%")
                args['acc'] = float(acc)
                continue
            except ValueError:
                await context.message.reply(f"Arguments must be numeric!")
                return

        elif not msg[index+1].isnumeric():
            await context.message.reply(f"Arguments must be numeric!")
            return

        args[msg[index][1:]] = int(msg[index+1])

    if not 'id' in args:
        await context.message.reply(f"Please provide a valid beatmap id!")
        return

    if not (beatmap_file := app.session.storage.get_beatmap(args['id'])):
        await context.message.reply(f"The requested beatmap was not found.")
        return

    perf = Performance(lazer=False)
    beatmap = Beatmap(bytes=beatmap_file)
    beatmap.convert(performance.convert_mode(args.get('mode', 0)), args.get('mods', 0))

    functions = {
        'acc': perf.set_accuracy,
        'mods': perf.set_mods,
        'combo': perf.set_combo,
        'n300': perf.set_n300,
        'n100': perf.set_n100,
        'n50': perf.set_n50,
        'katu': perf.set_n_katu,
        'geki': perf.set_n_geki,
        'miss': perf.set_misses
    }

    for key, value in args.items():
        if key in functions:
            functions[key](value)

    result = perf.calculate(beatmap)
    await context.message.reply(f"PP: {result.pp:.2f}")
