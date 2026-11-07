from dotenv import load_dotenv
from os import getenv

load_dotenv()

TOKEN = getenv('DISCORD_BOT_TOKEN') or getenv('TOKEN')
MONGO_URL = getenv('MONGO_URL')
DATABASE_PROVIDER = getenv('DATABASE_PROVIDER', 'mongodb').strip().lower()
OPS_LOG_HUB_URL = getenv('OPS_LOG_HUB_URL')
OPS_LOG_HUB_KEY = getenv('OPS_LOG_HUB_KEY')
OPS_LOG_PROJECT = getenv('OPS_LOG_PROJECT', 'discordbot-auto-reaction')
OPS_LOG_ENVIRONMENT = getenv('OPS_LOG_ENVIRONMENT', 'development')

if not TOKEN:
    raise RuntimeError('DISCORD_BOT_TOKEN environment variable is required')

if DATABASE_PROVIDER in ('mongo', 'mongodb') and not MONGO_URL:
    raise RuntimeError('MONGO_URL environment variable is required')
