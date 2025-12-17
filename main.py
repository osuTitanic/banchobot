
from app.common.logging import Console, File
from app.session import config

import logging
import app

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s',
    handlers=[Console, File]
)

def main():
    if not config.ENABLE_DISCORD_BOT or not config.DISCORD_BOT_TOKEN:
        logging.warning("BanchoBot is disabled, exiting...")
        exit(0)

    app.bot.run()

if __name__ == "__main__":
    main()
