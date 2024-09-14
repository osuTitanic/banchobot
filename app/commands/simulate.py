
from titanic_pp_py import Calculator, Beatmap
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

        argument_name = msg[index][1:]

        if argument_name not in possible_args:
            await context.message.reply(f"Unknown argument {msg[index]}! \nList of available arguments: {', '.join(possible_args)}")
            return

        if argument_name == "mods":
            args['mods'] = Mods.from_string(msg[index+1])
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
        await context.message.reply(f"Provide beatmap id!")
        return

    if not (beatmap_file := app.session.storage.get_beatmap(args['id'])):
        await context.message.reply(f"Can't find beatmap!")
        return

    calc = Calculator(
        mode=args['mode']
        if 'mode' in args else 0
    )

    functions = {
        'acc': calc.set_acc,
        'mods': calc.set_mods,
        'combo': calc.set_combo,
        'n300': calc.set_n300,
        'n100': calc.set_n100,
        'n50': calc.set_n50,
        'katu': calc.set_n_katu,
        'geki': calc.set_n_geki,
        'miss': calc.set_n_misses
    }

    for key, value in args.items():
        if key in functions:
            functions[key](value)

    bm = Beatmap(bytes=beatmap_file)

    result = calc.performance(bm)
    await context.message.reply(f"PP: {result.pp:.2f}")
