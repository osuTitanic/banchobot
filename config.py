
import dotenv
import os

dotenv.load_dotenv(override=False)

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST')

POSTGRES_POOLSIZE = int(os.environ.get('POSTGRES_POOLSIZE', 10))
POSTGRES_POOLSIZE_OVERFLOW = int(os.environ.get('POSTGRES_POOLSIZE_OVERFLOW', 30))

S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
S3_BASEURL    = os.environ.get('S3_BASEURL')

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

ENBALE_DISCORD_BOT = eval(os.environ.get('ENBALE_DISCORD_BOT', 'True').capitalize())
BOT_PREFIX = os.environ.get('DISCORD_BOT_PREFIX')
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_EMAIL = os.environ.get('SENDGRID_EMAIL')

MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
MAILGUN_EMAIL = os.environ.get('MAILGUN_EMAIL', '')
MAILGUN_URL = os.environ.get('MAILGUN_URL', 'api.eu.mailgun.net')
MAILGUN_DOMAIN = MAILGUN_EMAIL.split('@')[-1]

EMAILS_ENABLED = MAILGUN_API_KEY is not None or SENDGRID_API_KEY is not None
EMAIL = MAILGUN_EMAIL or SENDGRID_EMAIL

OFFICER_WEBHOOK_URL = os.environ.get('OFFICER_WEBHOOK_URL')
EVENT_WEBHOOK_URL = os.environ.get('EVENT_WEBHOOK_URL')
OSU_API_KEY = os.environ.get('OSU_API_KEY')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

APPROVED_MAP_REWARDS = eval(os.environ.get('APPROVED_MAP_REWARDS', 'False').capitalize())
S3_ENABLED = eval(os.environ.get('ENABLE_S3', 'True').capitalize())
DEBUG = eval(os.environ.get('DEBUG', 'False').capitalize())

DATA_PATH = os.path.abspath('.data')
VERSION = 'dev'
