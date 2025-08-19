
from app.common.logging import Console, File

import logging
import config
import utils
import app

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s',
    handlers=[Console, File]
)

def main():
    if not config.ENABLE_DISCORD_BOT:
        logging.warning("BanchoBot is disabled, exiting...")
        exit(0)

    utils.setup()
    app.bot.run()

if __name__ == "__main__":
    main()
