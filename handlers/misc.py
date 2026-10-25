from telegram import (Update,
                      InlineKeyboardButton,
                      InlineKeyboardMarkup,
                      InputMediaPhoto
                      )
from telegram.ext import (ApplicationBuilder,
                          ContextTypes,
                          CommandHandler,
                          filters,
                          MessageHandler,
                          ConversationHandler,
                          CallbackQueryHandler,
                          
                          )

import logging
from user_manager import UserManager
from constants import BOT_TOKEN, DEFAULT_QUOTA, DEFAULT_PHOTO, QUALITY_PROFILE_1080P
from helpers import(
    radarr_add_notification,
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# set higher logging level for httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

#error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error

    # Log only one line, without the traceback
    logger.warning(
        "Bot error: %s: %s",
        type(error).__name__,
        str(error).replace("\n", " ")
    )

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! to start asking for a movie, write /movie")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = ""

    #Check if user is admin or owner
    user = UserManager(update, context)
    users = context.bot_data.get("users", [])

    if user.id in users:
        role = user.get_role(user.id)
        if role == "admin" or role == "owner":
            msg = "List of owner/admin commands:\n/users - list users\n" \
            "/set_role (user_id) (role) - changes role of user\n" \
            "/set_quota (user_id) (quota) - changes quota of user\n"
    msg = msg + " Write command /movie to start adding movies and /series for series\n" \
                "/notif (on/off) - enable or disable notifications"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Unknown command!")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.bot_data.get("users", {})
    #user_names = {}
    #for user in users:
    #    user_names.setdefault(users[user]["name"], users[user]["role"])
    text = "List of users:\n" + "\n".join(
        f"ID: {user_id}, "
        f"Name: {user['name']}, "
        f"Role: {user['role']}, "
        f"Quota: {user['quota']}, "
        f"Notif_movie: {user['notif_movie']}\n"
        for user_id, user in users.items()
    ) 

    await update.message.reply_html(
        text=text
    )

async def claim_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """claiming ownerhip of bot"""
    user = UserManager(update, context)
    user.add_user()
    if "owner" in context.bot_data:
        logger.info("There already exist a owner for this bot")
        await update.message.reply_html(text="There already is an owner for this bot")
        return
    else:
        logger.info(f"User: {user.user.full_name} claimed ownership of this bot")
        await update.message.reply_html(text="You are now owner of this bot!")
        context.bot_data.setdefault("owner", user.id)

    users = context.bot_data.get("users", {})
    for user_id in users:
        if user_id == user.id:
            users[user_id]["role"] = "owner"

    # add notifications
    extra_dict = {}
    extra_dict.setdefault("onHealthIssue", True)
    extra_dict.setdefault("onHealthRestored", True)
    extra_dict.setdefault("includeHealthWarnings", True)
    radarr_add_notification(update, context, extra=extra_dict)

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Changes role of a users"""

    logger.info(f"set_role called with args: {context.args}")
    manager = UserManager(update, context)
    users = context.bot_data["users"]

    args = context.args
    if len(args) < 2 or len(args) > 2:
        # wrong number of args
        await update.message.reply_html(text=f"Expected 2 arguments, got {len(args)}")
        return

    user_id = args[0]
    # check if user_id is digit
    if not user_id.isdigit():
        await update.message.reply_text(text="user_id must be a digit")
        return

    user_id = int(user_id)
    # check first argument
    if user_id not in users:
        await update.message.reply_html(text="user_id is not known to bot, check /users")
        return

    # check second argument
    valid_first_args = ["admin", "user"]
    new_role = args[1].strip().lower()
    if new_role not in valid_first_args:
        await update.message.reply_html(text="Not a valid role. Must be admin or user")
        return

    
    # check role of target user
    if manager.isOwner(user_id):
        await update.message.reply_html(text="Cant change role of owner")
        logger.warning("Cant change role of owner")
        return

    
    if await manager.edit_role(new_role, user_id):
        logger.info(f"Changeing role for {user_id} to {new_role}")
        await update.message.reply_html(text=f"Changeing role for {user_id} to {new_role}")
    else:
        await update.message.reply_html(text="Failed to set new role")

async def edit_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    logger.info(f"edit_quota was called with args: {context.args}")
    manager = UserManager(update, context)
    args = context.args

    if len(args) > 2 or len(args) < 2:
        await update.message.reply_html(text=f"got {len(args)} arguments, expected 2")
        return
    
    if not args[0].isnumeric():
        await update.message.reply_html(text="argument target_user_id is not a number")
        return
    
    target_user_id = int(args[0])
    users = context.bot_data.get("users", {})
    if target_user_id not in users:
        await update.message.reply_html(text=f"User id: {target_user_id} is not known user.")
        return

    if not args[1].isnumeric():
        await update.message.reply_html(text="argument new_quota is not a number")
        return
    
    new_quota = int(args[1])

    await manager.set_quota(target_user_id, new_quota)

async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get status of recent movies"""
    return

#misc handlers
start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', help)
caps_handler = CommandHandler('caps', caps)
list_users_handler = CommandHandler('users', list_users)
claim_owner_handler = CommandHandler('claim', claim_owner)
set_role_handler = CommandHandler('set_role', set_role)
unknown_handler = MessageHandler(filters.COMMAND, unknown)
edit_quota_handler = CommandHandler('set_quota', edit_quota)
