import os
from dotenv import load_dotenv

QUALITY_PTOFILE_1080P = 4
DEFAULT_QUOTA = 0
DEFAULT_PHOTO = "https://w7.pngwing.com/pngs/116/765/png-transparent-clapperboard-computer-icons-film-movie-poster-angle-text-logo-thumbnail.png"

# config variables
load_dotenv(dotenv_path="sonarr_test_config.env")
BOT_TOKEN = os.getenv('BOT_TOKEN')

SONARR_API_KEY = os.getenv('SONARR_API_KEY')
SONARR_HOST = os.getenv('SONARR_HOST')
SONARR_PORT = os.getenv('SONARR_PORT')

RADARR_API_KEY = os.getenv('RADARR_API_KEY')
RADARR_HOST = os.getenv('RADARR_HOST')
RADARR_PORT = os.getenv('RADARR_PORT')

#build default users
DEFAULT_USERS = {}

# Owner
owner_string = os.getenv("OWNER_ID")
owner_id = None
owner_name = None

if owner_string:
    owner_id, owner_name = owner_string.split(":", 1)
    owner_id = int(owner_id)
    owner_name = owner_name.replace("_", " ").strip()
    DEFAULT_USERS.setdefault(owner_id, {
                "role": "owner",
                "username": None,
                "name": owner_name,
                "quota": DEFAULT_QUOTA,
                "notif": True,
                "allowedSeries": True
                })


# Admins
admin_string = os.getenv("ADMIN_ID")
admins = []

if admin_string:
    admins = [
        (int(admin_id), name.replace("_", " "))
        for entry in admin_string.split(",")
        for admin_id, name in [entry.split(":", 1)]
    ]


#add admin
for id, name in admins:
    DEFAULT_USERS.setdefault(id, {
            "role": "admin",
            "username": None,
            "name": name,
            "quota": DEFAULT_QUOTA,
            "notif": True,
            "allowedSeries": True
            })