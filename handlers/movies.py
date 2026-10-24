from telegram import (Update,
                      InlineKeyboardButton,
                      InlineKeyboardMarkup,
                      InputMediaPhoto
                      )
from telegram.ext import (
                          ContextTypes,
                          CommandHandler,
                          filters,
                          MessageHandler,
                          ConversationHandler,
                          CallbackQueryHandler,
                          
                          )
from datetime import (
    datetime,
)
import logging
from user_manager import UserManager
from radarr import RadarrClient
from constants import BOT_TOKEN, DEFAULT_QUOTA, DEFAULT_PHOTO, QUALITY_PROFILE_1080P
from helpers import(
    get_user,
    get_tag,
    add_notification,
    ping_radarr,
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# config variables
MAX_OVERVIEW_CHARS = 75

# set higher logging level for httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

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
                InlineKeyboardButton(text="No", callback_data="next_-1"),
                InlineKeyboardButton(text="yes", callback_data=f"add_{current_index}")
            ]
        ]
        await query.edit_message_caption(
            caption=f"you selected {context.user_data["movies"][current_index]["title"]}. Are you sure?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_MOVIE
    elif action == "movie":
        await query.edit_message_text(
            text="What movie do you want?",
            reply_markup=None
        )
        return None

    keyboard = [
        [
            InlineKeyboardButton(text="cancel",
                                 callback_data=f"cancel_{current_index}"),
            InlineKeyboardButton(text="prev",
                                 callback_data=f"prev_{current_index}"),
            InlineKeyboardButton(text="next",
                                 callback_data=f"next_{current_index}"),
            InlineKeyboardButton(text="select",
                                 callback_data=f"select_{current_index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    default_photo = DEFAULT_PHOTO
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
ENTRY_MOVIE, SELECT_MOVIE = range(2)

# Movies
async def movie_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of movie conversation!"""
    logger.info("Entry of movie conversation")

    # check users
    user = UserManager(update, context)
    users = context.bot_data.setdefault("users", {})

    # See if radarr is reachable
    if not ping_radarr(context):
        await update.message.reply_text("Radarr not reachable, check connection or config file")
        return ConversationHandler.END

    # check if user is new
    if user.id not in users:
        #user doesnt exist
        user.add_user()
        tag = get_tag(update, context)
        onDownload = context.bot_data["users"][user.id]["notif"]
        add_notification(update, context, tag["id"], extra={"onDownload": onDownload})

    # check quotas
    if await user.met_quota() and user.get_role() == "user":
        return ConversationHandler.END

    await update.message.reply_html(
        text="what movie do you want to add?",
        reply_markup=None
    )
    return SELECT_MOVIE

async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gives the user movies to select from"""
    logger.info("entering select_movie function in convohandler")
    movies = context.bot_data["radarrClient"].search_movie(update.message.text)
    if not movies:
        logger.info("found no search result for %s", update.message.text)
        await update.message.reply_html(
            text=f"Did not find any movies with query: {update.message.text} \n Try again or /cancel: "
        )
        return SELECT_MOVIE

    context.user_data["movies"] = movies
    logger.info("found %s search result for movie %s", len(movies),
                update.message.text)

    index = 0
    keyboard = [
        [
            InlineKeyboardButton(text="cancel",
                                 callback_data=f"cancel_{index}"),
            InlineKeyboardButton(text="prev",
                                 callback_data=f"prev_{index}"),
            InlineKeyboardButton(text="next",
                                 callback_data=f"next_{index}"),
            InlineKeyboardButton(text="select",
                                 callback_data=f"select_{index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    movie = movies[index]
    overview = movie["overview"]
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview[:MAX_OVERVIEW_CHARS] + "..."

    default_photo = DEFAULT_PHOTO
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

    radarr = context.bot_data["radarrClient"] # type: RadarrClient
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
            qualityProfileId=QUALITY_PROFILE_1080P,
            tags=[tag["id"]]
            )
        
        await update.callback_query.edit_message_caption(
            caption="Movie Added!"
        )
        recent_movie_list = context.user_data.get("recent movies", [])
        new_data = (movie["tmdbId"], datetime.now())
        recent_movie_list.append(new_data)
        context.user_data["recent movies"] = recent_movie_list
    
    context.user_data["movies"].clear()
    return ConversationHandler.END

async def notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager = UserManager(update, context)
    user = get_user(update)
    users = context.bot_data["users"]
    radarr = context.bot_data["radarrClient"] # type: RadarrClient
    current_onDOwnload = users[manager.id]["notif"]
    logger.info(f"{user.first_name} called notif with args: {context.args}")

    args = context.args
    if len(args) > 1 or len(args) < 1:
        # wrong number of args
        await update.message.reply_html(text=f"Expected 1 arguments, got {len(args)}")
        return

    arg = args[0]
    if arg != "on" and arg != "off":
        await update.message.reply_html(text="invalid argument. valid arguments is 'on' or 'off'")

    onDownload = True if arg == "on" else False
    if onDownload == current_onDOwnload:
        #no change, do nothing
        logger.info(f"notif is already {onDownload}")
        await update.message.reply_html(text=f"Notifications is already {onDownload}")
        return

    #else edit notification
    users[manager.id]["notif"] = onDownload
    name = user.first_name.lower() + ":" + str(user.id)
    logger.info(f"notif changes to {onDownload}")
    await update.message.reply_html(text=f"Notifications changed to {onDownload}")
    radarr.edit_telegram_notification(id=None, name=name, data={"onDownload": onDownload} )
    return

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    user = get_user(update)
    query = update.callback_query
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END


#  movie handlers.
movie_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('movie', movie_entry)],
        states={
            SELECT_MOVIE: [MessageHandler(filters.TEXT and (~filters.COMMAND), select_movie)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
movie_button_handler = CallbackQueryHandler(callback=button, pattern="^(select|add|next|prev|cancel)_")
notif_handler = CommandHandler('notif', notif)
##################