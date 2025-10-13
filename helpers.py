from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from constants import BOT_TOKEN, DEFAULT_QUOTA
from user_manager import UserManager
import logging

logger = logging.getLogger(__name__)




# help functions
def get_user(update: Update):
    if update.message:
        return update.message.from_user
    elif update.callback_query:
        return update.callback_query.from_user


def get_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adds user tag to movie"""
    logger.debug("Getting tag...")

    user = str(get_user(update).first_name).lower()
    label = user + ":" + str(update.effective_chat.id).lower()

    # Post_tag will return a tag if it already exsists
    radarr = context.bot_data["radarrClient"]
    return radarr.post_tag(label)


def add_notification(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     tagId: int = None, extra = None):
    """Adds notifications to radarr"""
    r = context.bot_data["radarrClient"]
    user = get_user(update)
    chatId = str(update.effective_chat.id).lower()
    name = user.first_name.lower() + ":" + str(user.id)
    return r.add_telegram_notification(
        name,
        botToken=BOT_TOKEN,
        chatId=chatId,
        tagId=tagId,
        extra=extra
     )


async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update)
    user_id = user.id
    users = context.bot_data.setdefault("users", {})

    # Add to list of users
    if user_id not in users:
        logger.info(f"adding user: {user.full_name} to list of user")
        context.bot_data["users"].setdefault(user_id, {
          "role": "user",
          "username": user.username,
          "name": user.full_name,
          "quota": DEFAULT_QUOTA
        })


def update_recent_movies(context: ContextTypes.DEFAULT_TYPE):
    """Updated recent movielist"""
    current_list = context.user_data.get("recent movies", [])
    limit = datetime.now() - timedelta(days=7)
    new_list = [t for t in current_list if t > limit]
    context.user_data.setdefault("recent movies", new_list)
