
import logging
import app

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s'
)

def main():
    app.bot.run()

if __name__ == "__main__":
    main()
