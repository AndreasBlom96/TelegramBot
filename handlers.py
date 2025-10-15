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
                          CallbackQueryHandler
                          )
from datetime import (
    datetime,
)
import logging
from user_manager import UserManager
from radarr import RadarrClient
from constants import BOT_TOKEN, DEFAULT_QUOTA
from helpers import(
    get_user,
    get_tag,
    add_notification,
)

# config variables
MAX_OVERVIEW_CHARS = 75


# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# set higher logging level for httpx
logging.getLogger("httpx").setLevel(logging.WARNING)


# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! to start asking for a movie, write /movie")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Write command /movie to start adding movie"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Unknown command!")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = context.bot_data.get("users", {})
    user_names = {}
    for user in users:
        user_names.setdefault(users[user]["name"], users[user]["role"])

    await update.message.reply_html(
        text=f"list of users: {users}"
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
    add_notification(update, context, extra=extra_dict)


async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Changes role of a users"""

    manager = UserManager(update, context)
    users = context.bot_data["users"]

    args = context.args
    if len(args) < 2 or len(args) > 2:
        # wrong number of args
        await update.message.reply_html(text=f"exptected 2 arguments, got {len(args)}")
        return

    # check first argument
    valid_first_args = ["admin", "user"]
    if args[0] not in valid_first_args:
        await update.message.reply_html(text="not a valid role. Must be admin or user")
        return
    new_role = args[0]

    user_id = int(args[1])
    # check second argument
    if user_id not in users:
        await update.message.reply_html(text="user_id is not known to bot, check /users")
        return

    # check role of target user
    if manager.isOwner(user_id):
        await update.message.reply_html(text="Cant change role of owner")
        logger.warning("Cant change role of owner")
        return

    logger.info(f"Changeing role for {user_id} to {args[0]}")
    await manager.edit_role(new_role, user_id)   


async def edit_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
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

# Inline button
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    action = query.data.split("_")[0]
    current_index = int(query.data.split("_")[1])
    logger.info(f"action: {action}, index: {current_index}")

    if action == "next":
        current_index = (current_index+1) % (len(context.user_data["movies"]))
    elif action == "prev":
        current_index = (current_index-1) % (len(context.user_data["movies"]))
    elif action == "cancel":
        await query.edit_message_caption(
            caption="Canceling request, bye bye",
        )
        await query.delete_message()
        return await cancel(update, context)
    elif action == "add":
        await query.edit_message_caption(
            caption="Nice",
            reply_markup=None
        )
        return await add_movie(update, context)
    elif action == "select":
        context.user_data["selected_index"] = current_index

        keyboard = [
            [
                InlineKeyboardButton(text="yes", callback_data=f"add_{current_index}"),
                InlineKeyboardButton(text="No", callback_data="next_-1")
            ]
        ]
        await query.edit_message_caption(
            caption=f"you selected {context.user_data["movies"][current_index]["title"]}. Are you sure?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT
    elif action == "movie":
        await query.edit_message_text(
            text="What movie do you want?",
            reply_markup=None
        )
        return None

    keyboard = [
        [
            InlineKeyboardButton(text="select",
                                 callback_data=f"select_{current_index}"),
            InlineKeyboardButton(text="next",
                                 callback_data=f"next_{current_index}"),
            InlineKeyboardButton(text="prev",
                                 callback_data=f"prev_{current_index}"),
            InlineKeyboardButton(text="cancel",
                                 callback_data=f"cancel_{current_index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    default_photo = "https://w7.pngwing.com/pngs/116/765/png-transparent-clapperboard-computer-icons-film-movie-poster-angle-text-logo-thumbnail.png"
    photo_url = default_photo

    movie = context.user_data["movies"][current_index]

    if movie["images"]:
        photo_url = movie["images"][0]["remoteUrl"]

    overview = movie["overview"]
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview[:MAX_OVERVIEW_CHARS] + "..."

    await query.edit_message_media(media=InputMediaPhoto(photo_url))
    await query.edit_message_caption(
        f'{movie["title"]}, year: {movie["year"]} \n\n{overview}',
        reply_markup=markup
        )

# conversations
ENTRY, SELECT = range(2)


async def movie_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of conversation!"""
    logger.info("Entry of conversation")

    # check users
    user = UserManager(update, context)
    user.add_user()

    # check quotas
    if await user.met_quota():
        return ConversationHandler.END

    await update.message.reply_html(
        text="what movie do you want to add?",
        reply_markup=None
    )
    return SELECT


async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gives the user movies to select from"""
    logger.info("entering select_movie function in convohandler")
    movies = context.bot_data["radarrClient"].search_movie(update.message.text)
    if not movies:
        logger.info("found no search result for %s", update.message.text)
        await update.message.reply_html(
            text=f"Did not find any movies with query: {update.message.text} \n Try again or /cancel: "
        )
        return SELECT

    context.user_data["movies"] = movies
    logger.info("found %s search result for movie %s", len(movies),
                update.message.text)

    index = 0
    keyboard = [
        [
            InlineKeyboardButton(text="select",
                                 callback_data=f"select_{index}"),
            InlineKeyboardButton(text="next",
                                 callback_data=f"next_{index}"),
            InlineKeyboardButton(text="prev",
                                 callback_data=f"prev_{index}"),
            InlineKeyboardButton(text="cancel",
                                 callback_data=f"cancel_{index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    movie = movies[index]
    overview = movie["overview"]
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview[:MAX_OVERVIEW_CHARS] + "..."

    default_photo = "https://w7.pngwing.com/pngs/116/765/png-transparent-clapperboard-computer-icons-film-movie-poster-angle-text-logo-thumbnail.png"
    photo_url = default_photo
    if movie["images"]:
        photo_url = movie["images"][0]["remoteUrl"]

    await update.message.reply_photo(
        caption=f"{movie["title"]}, year: {movie["year"]} \n\n{overview}",
        photo=photo_url,
        reply_markup=markup
    )

    return ConversationHandler.END


async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add the movie to radarr"""

    radarr = context.bot_data["radarrClient"]
    movie_number = context.user_data["selected_index"]
    movie = context.user_data["movies"][movie_number]

    user = get_user(update)
    logger.info("User %s chose the movie %s.", user.full_name, movie["title"])

    # check if movie already exist in radarr
    # this check is already done in radarr.py and shoulc be removed here....
    search_result = radarr.get_added_movies({"tmdbId": movie["tmdbId"]})
    if search_result:
        await update.callback_query.edit_message_caption(
            caption="Movie already exists!"
        )
    else:
        tag = get_tag(update, context)
        radarr.add_movie(
            title=movie["title"],
            tmdbId=movie["tmdbId"],
            rootFolderPath=radarr.rootFolder,
            qualityProfileId=4,
            tags=[tag["id"]]
            )
        add_notification(update, context, tag["id"], extra={"onDownload": True})
        await update.callback_query.edit_message_caption(
            caption="Movie Added!"
        )
        recent_movie_list = context.user_data.get("recent movies", [])
        recent_movie_list.append(datetime.now())
        context.user_data["recent movies"] = recent_movie_list
    
    context.user_data["movies"].clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = get_user(update)
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END


conv_handler = ConversationHandler(
        entry_points=[CommandHandler('movie', movie_entry)],
        states={
            SELECT: [MessageHandler(filters.TEXT and (~filters.COMMAND), select_movie)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', help)
caps_handler = CommandHandler('caps', caps)
list_users_handler = CommandHandler('users', list_users)
claim_owner_handler = CommandHandler('claim', claim_owner)
set_role_handler = CommandHandler('set_role', set_role)
unknown_handler = MessageHandler(filters.COMMAND, unknown)
movie_button_handler = CallbackQueryHandler(button)
edit_quota_handler = CommandHandler('set_quota', edit_quota)


if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.bot_data["radarrClient"] = RadarrClient()


    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(caps_handler)
    application.add_handler(list_users_handler)
    application.add_handler(claim_owner_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(set_role_handler)

    application.add_handler(unknown_handler)
    application.run_polling()
