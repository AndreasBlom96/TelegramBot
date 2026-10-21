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
from datetime import (
    datetime,
)
import logging
from user_manager import UserManager
from radarr import RadarrClient
from sonarr import SonarrClient
from serie import SerieManager
from constants import BOT_TOKEN, DEFAULT_QUOTA, DEFAULT_PHOTO, QUALITY_PTOFILE_1080P
from helpers import(
    get_user,
    get_tag,
    add_notification,
)

# config variables
CHECK_CHAR = '✅'
UNCHECK_CHAR = '⬜'
MAX_OVERVIEW_CHARS = 75


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
        f"Notif: {user['notif']}\n"
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
    add_notification(update, context, extra=extra_dict)

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
            qualityProfileId=4,
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
    logger.info(f"notif called with args: {context.args}")
    manager = UserManager(update, context)
    user = get_user(update)
    users = context.bot_data["users"]
    radarr = context.bot_data["radarrClient"] # type: RadarrClient
    current_onDOwnload = users[manager.id]["notif"]

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
        return

    #else edit notification
    users[manager.id]["notif"] = onDownload
    name = user.first_name.lower() + ":" + str(user.id)
    logger.info(f"notif changes to {onDownload}")
    radarr.edit_telegram_notification(id=None, name=name, data={"onDownload": onDownload} )
    return

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    user = get_user(update)
    query = update.callback_query
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END

# conversations
ENTRY_SERIES, SELECT_SERIES = range(2)

#TODO
#add tagging...
#add notifaction
#fix such that if serie is already added, we modify instead.

async def series_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of series converation"""
    # check users
    user = UserManager(update, context)
    users = context.bot_data.setdefault("users", {})

    logger.info(f"User {user.user.full_name} enters series conversation")

    # check if user is new
    if user.id not in users:
        #user doesnt exist
        user.add_user()
        tag = get_tag(update, context)
        #Fix sonarr notification here

    #Implement check to see if user is allowed to here
    allowed_series = context.bot_data.get("users").get("allowedSeries", False)
    if not allowed_series and (user.get_role() == "user"):
        await update.message.reply_text("You don't have permission to add series. Ask Admin/Owner about permission")
        return ConversationHandler.END

    await update.message.reply_html(
            text="what series do you want to add?",
            reply_markup=None
        )
    return SELECT_SERIES

async def select_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("entering select_series function in convohandler")
    series = context.bot_data["sonarrClient"].search_series(update.message.text)
    if not series:
        logger.info("found no search result for %s", update.message.text)
        await update.message.reply_html(
             text=f"Did not find any series with query: {update.message.text} \n Try again or /cancel: "
        )
        return SELECT_SERIES
    
    context.user_data["series"] = series
    logger.info("found %s search result for serie %s", len(series),
                update.message.text)

    index = 0
    keyboard = [
        #Row 1
        [
            InlineKeyboardButton(text="cancel",
                                    callback_data=f"series_cancel_{index}"),
            InlineKeyboardButton(text="select",
                                    callback_data=f"series_select_{index}")
        ],
        #Row 2
        [
            InlineKeyboardButton(text="prev",
                                     callback_data=f"series_prev_{index}"),
            InlineKeyboardButton(text="next",
                                    callback_data=f"series_next_{index}"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    serie = series[index]
    overview = serie["overview"]
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview[:MAX_OVERVIEW_CHARS] + "..."
    
    default_photo = DEFAULT_PHOTO
    photo_url = default_photo
    if serie["images"]:
        photo_url = serie["images"][0]["remoteUrl"]
    
    await update.message.reply_photo(
        caption=f"{serie["title"]}, year: {serie["year"]}, status: {serie["status"]} \n\n{overview}",
        photo=photo_url,
        reply_markup=markup
    )
    
    return ConversationHandler.END

async def browse_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses prev or next CallbackQuery to browse series"""
    query = update.callback_query
    await query.answer()
    action = query.data.split("_")[1]
    current_index = int(query.data.split("_")[2])
    logger.info(f"Serie: action: {action}, index: {current_index}")

    if action == "next":
        current_index = (current_index + 1) % (len(context.user_data["series"]))
    elif action == "prev":
        current_index = (current_index - 1) % (len(context.user_data["series"]))
    else:
        logger.error(f"This should be unreachable. Browse action is neither next or prev..")

    keyboard = [
            #Row 1
            [
                InlineKeyboardButton(text="cancel",
                                        callback_data=f"series_cancel_{current_index}"),
                InlineKeyboardButton(text="select",
                                        callback_data=f"series_select_{current_index}")
            ],
            #Row 2
            [
                InlineKeyboardButton(text="prev",
                                         callback_data=f"series_prev_{current_index}"),
                InlineKeyboardButton(text="next",
                                        callback_data=f"series_next_{current_index}"),
            ]
        ]
    markup = InlineKeyboardMarkup(keyboard)


    serie = context.user_data["series"][current_index]
    overview = serie.get("overview", "Missing overview")
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview[:MAX_OVERVIEW_CHARS] + "..."
        
    default_photo = DEFAULT_PHOTO
    photo_url = default_photo
    if serie["images"]:
        photo_url = serie["images"][0]["remoteUrl"]
        
    await query.edit_message_media(media=InputMediaPhoto(photo_url))
    await query.edit_message_caption(
            f'{serie["title"]}, year: {serie["year"]}, status: {serie["status"]} \n\n{overview}',
            reply_markup=markup
            )

#TODO
#make the keyboard a for loop that takes values from a list instead?
async def select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """choose with season to monitor"""
    query = update.callback_query
    await query.answer()
    action = query.data.split("_")[1]
    current_index = int(query.data.split("_")[2])
    logger.info(f"Serie: action: {action}, index: {current_index}")

    #save selected index
    context.user_data["series_selected_index"] = current_index

    #start menu conversation about what seasons to download
    keyboard = [
            #Row All
            [
                InlineKeyboardButton(text="All",
                                    callback_data=f"series_monitor_all")
            ],
            #Row first season
            [
                InlineKeyboardButton(text="First Season",
                                    callback_data=f"series_monitor_firstSeason")
            ],
            #Row latest season
            [
                InlineKeyboardButton(text="latest Season",
                                    callback_data=f"series_monitor_latestSeason")
            ],
            #Row last season
            [
                InlineKeyboardButton(text="last Season (only if status: ended)",
                                    callback_data=f"series_monitor_lastSeason")
            ],
            #Row future season
            [
                InlineKeyboardButton(text="Future seasons",
                                    callback_data=f"series_monitor_future")
            ],
            #Row special season
            [
                InlineKeyboardButton(text="Specify for each season",
                                    callback_data=f"series_special_monitor")
            ],
            #Row cancel or go back
            [
                InlineKeyboardButton(text="cancel",
                                    callback_data=f"series_cancel"),
                InlineKeyboardButton(text="back",
                                    callback_data=f"series_next_-1")
            ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_caption(caption= "choose which seasons to monitor", reply_markup= markup)

async def monitor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """choose with season to monitor"""
    query = update.callback_query
    await query.answer()
    logger.info(f"season monitor callback data: {query.data}")
    action = query.data.split("_")[1]
    monitor_seasons = query.data.split("_")[2]
    logger.info(f"Serie: monitor_chosen: {monitor_seasons}")

    selected_index = context.user_data["series_selected_index"]
    serie = context.user_data["series"][selected_index]
    serie = SerieManager(serie)
    sonarr = context.bot_data["sonarrClient"] # type: SonarrClient

    #get exising tag
    added_tags = serie.resource["tags"] #type: list
    user_tag_label = get_tag(update, context)
    sonarr_tags = sonarr.get_tags()
    print(sonarr_tags)
    for tag in sonarr_tags:
        if tag["label"] == user_tag_label:
            tag_id_to_add = tag["id"]
    tags = serie.resource["tags"].append(tag_id_to_add)

    sonarr.add_serie(serie, QUALITY_PTOFILE_1080P, monitor_seasons, tags=tags)
    context.user_data["series"].clear()
    await query.edit_message_caption(caption="Series added!", reply_markup=None)
    
async def series_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.delete_message() 
    await cancel(update, context)

async def series_special_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles if people want to specify monitoring for each season"""
    query = update.callback_query
    await query.answer()

    logger.debug(f"entered series special with data {query.data}")

    season_to_add = context.user_data.setdefault("seasons to add", []) # type: list
    #get callback data
    if ":" in query.data:
        toggle_s = int(query.data.split("_")[1])
        if toggle_s in season_to_add:
            season_to_add.remove(toggle_s)
        else:
            season_to_add.append(toggle_s)
    else:
        season_to_add = context.user_data.setdefault("seasons to add", [])
        context.user_data["seasons to add"].clear()
        

    selected_index = context.user_data["series_selected_index"]
    serie = context.user_data["series"][selected_index]
    number_of_seasons = len(serie.get("seasons", []))
    
    #construct keyboard
    keyboard = []
    row = []
    for s in range(1,number_of_seasons+1,):
        row.append(InlineKeyboardButton(text=f"S{s} {CHECK_CHAR if s in season_to_add else UNCHECK_CHAR}",
                                        callback_data=f"series:season_{s}",
                                        style="success" if s in season_to_add else None))
        if s % 3 == 0:
            keyboard.append(row)
            row = []
    keyboard.append(row)

    #last button
    last_buttons = [
        InlineKeyboardButton(text="back",
                            callback_data=f"series_select_0"),
        InlineKeyboardButton(text="Done",
                            callback_data=f"series_special_done")
    ]
    keyboard.append(last_buttons)

    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_caption(caption="press a season to toggle",
                                     reply_markup=markup)

async def add_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """special add with seasons"""
    query = update.callback_query
    await query.answer()

    selected_index = context.user_data["series_selected_index"] #type: int
    serie = context.user_data["series"][selected_index]

    serie = SerieManager(serie)
    sonarr = context.bot_data["sonarrClient"] # type: SonarrClient
    seasons_to_add = context.user_data["seasons to add"] # type: list
    sonarr.add_serie(serie, QUALITY_PTOFILE_1080P, monitor = "skip", seasons_to_add=seasons_to_add)

    #flush all data
    context.user_data["series"].clear()
    context.user_data.pop("seasons to add")
    context.user_data.pop("series_selected_index")
    await query.edit_message_caption(caption="Series added!", reply_markup=None)

# series handler
series_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('series', series_entry)],
    states={
        SELECT_SERIES: [MessageHandler(filters.TEXT and (~filters.COMMAND), select_series)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

series_browse_button = CallbackQueryHandler(callback=browse_series, pattern="^series_(next|prev)")
series_select_callback = CallbackQueryHandler(callback=select_callback, pattern="^series_select")
series_monitor_callback = CallbackQueryHandler(callback=monitor_callback, pattern="^series_monitor")
series_cancel = CallbackQueryHandler(callback=series_cancel_callback, pattern="^series_cancel")
series_special = CallbackQueryHandler(callback=series_special_monitor, pattern="^(series_special_monitor|series:season)")
series_add_specific_seasons = CallbackQueryHandler(callback=add_seasons, pattern="^series_special_done")
################## 

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

#misc handlers
start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', help)
caps_handler = CommandHandler('caps', caps)
list_users_handler = CommandHandler('users', list_users)
claim_owner_handler = CommandHandler('claim', claim_owner)
set_role_handler = CommandHandler('set_role', set_role)
unknown_handler = MessageHandler(filters.COMMAND, unknown)
edit_quota_handler = CommandHandler('set_quota', edit_quota)

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.bot_data["radarrClient"] = RadarrClient()
    application.bot_data["sonarrClient"] = SonarrClient()


    application.add_handler(movie_conv_handler)
    application.add_handler(series_conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(caps_handler)
    application.add_handler(list_users_handler)
    application.add_handler(claim_owner_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(set_role_handler)

    application.add_handler(unknown_handler)
    application.run_polling()
