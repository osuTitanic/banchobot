
import logging
import utils
import app

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s'
)

def main():
    utils.setup()
    app.bot.run()

if __name__ == "__main__":
    main()
