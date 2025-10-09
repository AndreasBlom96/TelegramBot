import os
from dotenv import load_dotenv

# config variables
load_dotenv(dotenv_path="config.env")
BOT_TOKEN = os.getenv('BOT_TOKEN')
DEFAULT_QUOTA = 5

RADARR_API_KEY = os.getenv('RADARR_API_KEY')
RADARR_HOST = os.getenv('RADARR_HOST')
RADARR_PORT = os.getenv('RADARR_PORT')