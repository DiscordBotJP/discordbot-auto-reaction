from dotenv import load_dotenv
from os import getenv

load_dotenv()

TOKEN = getenv('DISCORD_BOT_TOKEN') or getenv('TOKEN')
MONGO_URL = getenv('MONGO_URL')
OPS_LOG_HUB_URL = getenv('OPS_LOG_HUB_URL')
OPS_LOG_HUB_KEY = getenv('OPS_LOG_HUB_KEY')
OPS_LOG_PROJECT = getenv('OPS_LOG_PROJECT', 'discordbot-auto-reaction')
OPS_LOG_ENVIRONMENT = getenv('OPS_LOG_ENVIRONMENT', 'development')

if not TOKEN:
    raise RuntimeError('DISCORD_BOT_TOKEN environment variable is required')

if not MONGO_URL:
    raise RuntimeError('MONGO_URL environment variable is required')
