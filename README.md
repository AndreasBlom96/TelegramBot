# 🎬 Radarr Telegram Bot

A Telegram bot that integrates with **Radarr** to let users search, add, and manage movies — directly from chat.

---

## 🚀 Features
- 🔍 Search for movies via TMDb
- 🎞️ Add movies to Radarr from Telegram
- 👥 Role management — owner, admin, user
- 🎯 Weekly quotas for users
- 🛠️ Built using `python-telegram-bot` and `Radarr API`

---

## 🧰 Requirements
- Python 3.10+
- A running instance of [Radarr](https://radarr.video/)
- A Telegram bot token from [BotFather](https://t.me/BotFather)

---

## ⚙️ Installation

```bash
# 1️⃣ Clone this repo
git clone https://github.com/AndreasBlom96/TelegramBot
cd TelegramBot

# 2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Create config.env
cp exampleConfig.env config.env
