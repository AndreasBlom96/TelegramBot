# Radarr Telegram Bot

First bigger python project. There is a lot left to do but i dont really have the time! 
A Telegram bot that integrates with **Radarr** to let users search and add movies from chat.

---

## Features
- Search for movies and series
- Add movies and series to Radarr or Sonarr from Telegram
- Role management — owner, admin, user
- Weekly quotas for users
- Built using `python-telegram-bot`, `Requests`

---

## Requirements
- Python 3.10+
- A running instance of [Radarr](https://radarr.video/)
- A running instance of [Sonarr](https://radarr.video/)
- A Telegram bot token from [BotFather](https://t.me/BotFather)

---

## Installation

```bash
# Clone this repo
git clone https://github.com/AndreasBlom96/TelegramBot
cd TelegramBot

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create config.env
cp exampleConfig.env config.env (make sure constant.py points to correct config.env file)
#edit you config files with tokens and api keys

# Run bot!
python bot.py
```

---

## Telegram bot commands!
- /start --	Starts the bot
- /movie --	Search and add a movie
- /series -- search and add a series
- /users --	Lists all registered users
- /claim --	Claim bot ownership
- /set_role (user_id) (role) --	Change a users role
- /edit_quota (user_id) (quota) -- change a users quota
- /notif (on/off) -- turns notifications on/off

---

## TODO!
- setup persistance
- add commands:
  - /status
  - set series allowed for users
  - fix /notif so that it works for series also
- notifications might be a little wonky. not sure
