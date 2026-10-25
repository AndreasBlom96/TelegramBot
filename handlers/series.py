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
from sonarr import SonarrClient
from serie import SerieManager
from constants import BOT_TOKEN, DEFAULT_QUOTA, DEFAULT_PHOTO, QUALITY_PROFILE_1080P
from helpers import(
    get_user,
    get_tag,
    ping_sonarr,
    sonarr_add_notification,
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# set higher logging level for httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

# config variables
CHECK_CHAR = '✅'
UNCHECK_CHAR = '⬜'
MAX_OVERVIEW_CHARS = 75


# conversations
ENTRY_SERIES, SELECT_SERIES = range(2)

#TODO
#add notifaction
#add status?
async def series_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of series converation"""
    # check users
    user = UserManager(update, context)
    users = context.bot_data.setdefault("users", {})

    logger.info(f"User {user.user.full_name} enters series conversation")

    #reset user data
    context.user_data["modifying_series"] = False
    context.user_data["modifying_series_first_enter"] = True
    context.user_data["seasons to add"] = []
    if "series" in context.user_data:
        context.user_data["series"].clear()

    #check if sonarr is reachable
    if not ping_sonarr(context):
        await update.message.reply_text("Sonarr not reachable. Check connection or config file")
        return ConversationHandler.END

    # check if user is new
    tag = get_tag(update, context, get_sonar=True)
    if user.id not in users:
        user.add_user()
        
    #Fix sonarr notification here
    sonarr = context.bot_data["sonarrClient"] # type: SonarrClient
    if not sonarr.get_notification_by_name(tag["label"]):
        logger.info(f"Adding notificatione for {user.user.first_name}")
        onDownload = context.bot_data["users"][user.id]["notif_series"]
        sonarr_add_notification(update, context, tag["id"], extra={"onDownload": onDownload})

    #Implement check to see if user is allowed to here
    allowed_series = users.get(user.id).get("allowedSeries", False)
    if (not allowed_series) and (user.get_role() == "user"):
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

    serie = series[index] # type: dict
    overview = serie.get("overview", "Missing overview")
    if len(overview) > MAX_OVERVIEW_CHARS:
        overview = overview[:MAX_OVERVIEW_CHARS] + "..."
    
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
        overview = overview[:MAX_OVERVIEW_CHARS] + "..."
        
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

    #check if series is added
    serie_data = context.user_data["series"][current_index]
    serie = SerieManager(serie_data)
    sonarr = context.bot_data["sonarrClient"] #type: SonarrClient
    existing_serie = sonarr.get_added_series(tvdbId=serie_data["tvdbId"])
    if existing_serie:
        logger.info(f"Series already exist, entering editing mode")
        context.user_data["seasons to add"] = serie.get_monitored_seasons()
        context.user_data["modifying_series"] = True

    #start menu conversation about what seasons to download
    keyboard = [
            #Row All
            [
                InlineKeyboardButton(text="All",
                                    callback_data=f"series_monitor_all"
                                    )
            ],
            #Row first season
            [
                InlineKeyboardButton(text="First Season",
                                    callback_data=f"series_monitor_firstSeason"
                                    )
            ],
            #Row latest season
            [
                InlineKeyboardButton(text="latest Season",
                                    callback_data=f"series_monitor_latestSeason"
                                    )
            ],
            #Row last season
            [
                InlineKeyboardButton(text="last Season",
                                    callback_data=f"series_monitor_lastSeason"
                                    )
            ],
            #Row future season
            [
                InlineKeyboardButton(text="Future seasons",
                                    callback_data=f"series_monitor_future"
                                    )
            ],
            # existing
            [
                InlineKeyboardButton(text="existing",
                                     callback_data=f"series_monitor_existing"
                                    )
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

    if context.user_data["modifying_series"]:
        await query.edit_message_caption(caption="series already exist! Modifying monitoring", reply_markup=markup)
    else:
        await query.edit_message_caption(caption= "choose which seasons to monitor", reply_markup=markup)

async def monitor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """choose with season to monitor"""
    query = update.callback_query
    await query.answer()

    #Log and get callback data
    logger.info(f"season monitor callback data: {query.data}")
    action = query.data.split("_")[1]
    monitor_seasons = query.data.split("_")[2]
 
    # get selected series
    selected_index = context.user_data["series_selected_index"]
    selected_series_data = context.user_data["series"][selected_index]
    serie = SerieManager(selected_series_data)
    sonarr = context.bot_data["sonarrClient"] # type: SonarrClient

    # fix tags
    added_tags = serie.resource["tags"] #type: list
    user_tag_id = get_tag(update, context, get_sonar=True)["id"]
    if user_tag_id not in added_tags:
        added_tags.append(user_tag_id)

    if context.user_data["modifying_series"]:
        sonarr.edit_series(serie, monitor=monitor_seasons)
        await query.edit_message_caption(caption="Series modified!", reply_markup=None)
    else:
        sonarr.add_serie(serie, QUALITY_PROFILE_1080P, monitor_seasons, tags=added_tags)
        await query.edit_message_caption(caption="Series added!", reply_markup=None)
        
async def series_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.delete_message() 
    await cancel(update, context)

async def series_special_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles if people want to specify monitoring for each season"""
    query = update.callback_query
    await query.answer()

    logger.info(f"entered series special with data {query.data}")

    selected_index = context.user_data["series_selected_index"]
    serie_data = context.user_data["series"][selected_index]
    serie = SerieManager(serie_data)
    number_of_seasons = len(serie_data.get("seasons", [])) 

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
            
    #construct keyboard
    keyboard = []
    row = []
    for s in range(0,number_of_seasons):
        row.append(InlineKeyboardButton(text=f"S{s if s != 0 else "pecials"} {CHECK_CHAR if s in season_to_add else UNCHECK_CHAR}",
                                        callback_data=f"series:season_{s}",
                                        style="success" if s in season_to_add else None))
        if (s+1) % 3 == 0 and s != 0:
            keyboard.append(row)
            row = []
    keyboard.append(row)

    #last button
    last_buttons = [
        InlineKeyboardButton(text="back",
                            callback_data=f"series_select_0"),
        InlineKeyboardButton(text="Done, add series!",
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

    # get selected series
    selected_index = context.user_data["series_selected_index"] #type: int
    serie = context.user_data["series"][selected_index] #type: dict

    # fix tags
    added_tags = serie["tags"] #type: list
    user_tag_id = get_tag(update, context, get_sonar=True)["id"]
    if user_tag_id not in added_tags:
        added_tags.append(user_tag_id)

    seasons_to_add = context.user_data["seasons to add"] # type: list

    #check if series is added
    serie = SerieManager(serie) # type: SerieManager
    sonarr = context.bot_data["sonarrClient"] # type: SonarrClient
    if context.user_data["modifying_series"]:
        sonarr.edit_series(serie, seasons_to_add=seasons_to_add)
        await query.edit_message_caption(caption="Series edited!", reply_markup=None)
    else:
        sonarr.add_serie(serie, QUALITY_PROFILE_1080P, monitor = "skip", seasons_to_add=seasons_to_add, tags=added_tags)
        await query.edit_message_caption(caption="Series added!", reply_markup=None)

    # flush all data
    context.user_data["series"].clear()
    context.user_data.pop("seasons to add")
    context.user_data.pop("series_selected_index")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    user = get_user(update)
    query = update.callback_query
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END

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