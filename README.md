# Radarr Telegram Bot

First bigger python project. There is a lot left to do but i dont really have the time! 
A Telegram bot that integrates with **Radarr** to let users search and add movies from chat.

---

## Features
- Search for movies via TMDb
- Add movies to Radarr from Telegram
- Role management — owner, admin, user
- Weekly quotas for users
- Built using `python-telegram-bot` and `Radarr API`

---

## Requirements
- Python 3.10+
- A running instance of [Radarr](https://radarr.video/)
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
cp exampleConfig.env config.env
```

---

## Telegram bot commands!
- /start	Starts the bot
- /movie	Search and add a movie
- /users	Lists all registered users
- /claim	Claim bot ownership
- /set_role <role> <user_id>	Change a user’s role
- /edit_quota <user_id> <quota>

---

## TODO!
- setup persistance
- add commands:
  - /status
  - /unclaim?
- add more functionality with notifications
- in future add Sonarr also?
