
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

ENABLE_DISCORD_BOT = eval(os.environ.get('ENABLE_DISCORD_BOT', 'True').capitalize())
BOT_PREFIX = os.environ.get('DISCORD_BOT_PREFIX')
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_DOMAIN = EMAIL_SENDER.split('@')[-1]
EMAILS_ENABLED = bool(EMAIL_PROVIDER and EMAIL_SENDER)

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT') or '587')
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
MAILGUN_URL = os.environ.get('MAILGUN_URL', 'api.eu.mailgun.net')

OFFICER_WEBHOOK_URL = os.environ.get('OFFICER_WEBHOOK_URL')
EVENT_WEBHOOK_URL = os.environ.get('EVENT_WEBHOOK_URL')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

OSU_CLIENT_ID = os.environ.get('OSU_CLIENT_ID')
OSU_CLIENT_SECRET = os.environ.get('OSU_CLIENT_SECRET')

CHAT_WEBHOOK_CHANNELS = os.environ.get('ALLOWED_WEBHOOK_CHANNELS', '#osu').split(',')
CHAT_WEBHOOK_URL = os.environ.get('CHAT_WEBHOOK_URL')
CHAT_CHANNEL_ID = int(os.environ.get('CHAT_CHANNEL_ID', '0')) or None

APPROVED_MAP_REWARDS = eval(os.environ.get('APPROVED_MAP_REWARDS', 'False').capitalize())
S3_ENABLED = eval(os.environ.get('ENABLE_S3', 'True').capitalize())
DEBUG = eval(os.environ.get('DEBUG', 'False').capitalize())

DATA_PATH = os.path.abspath('.data')
VERSION = 'dev'
