from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from constants import BOT_TOKEN, DEFAULT_QUOTA
from user_manager import UserManager
from radarr import RadarrClient
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

    user_name = str(get_user(update).first_name).lower()
    label = user_name + ":" + str(update.effective_chat.id).lower()

    # Post_tag will return a tag if it already exsists
    radarr = context.bot_data["radarrClient"] # type: RadarrClient
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

