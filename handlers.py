import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler, ConversationHandler, CallbackQueryHandler
import logging
from radarr import RadarrClient
token_text = "sacredtexts.txt"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

#get secret stuff from hidden file...
def getToken(fileName):
    with open(fileName, "r") as file:
        content = file.readline().strip()
        #print(content)
        return content
    logger.error("Could not open txt file with bot token")
    return None

#Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! to start asking for a movie, write /get")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= "Write command /get to start adding movie")

async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text = text_caps)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text = "Unknown command!")

#messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


#conversations
CHOICE, MOVIE, SELECT, QUALITY = range(4)

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
    else:
        context.user_data["selected_tmdbID"] = context.user_data["movies"][current_index]["tmdbId"]
        return MOVIE

    keyboard = [
        [
        InlineKeyboardButton(text="select",callback_data= f"select_{current_index}"),
        InlineKeyboardButton(text="next", callback_data=f"next_{current_index}"),
        InlineKeyboardButton(text="prev", callback_data=f"prev_{current_index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    movie = context.user_data["movies"][current_index]
    await query.edit_message_media(media=InputMediaPhoto(movie["images"][0]["remoteUrl"]))
    await query.edit_message_caption(f"{movie["title"]}, year: {movie["year"]}", reply_markup=markup)

async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of conversation!"""
    reply_keyboard = [["movie", "series", "cancel"]]
    r = RadarrClient()
    context.user_data["radarrClient"] = r
    await update.message.reply_html(
        text= "Do you want a movie or series?",
        reply_markup= ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True,
            input_field_placeholder= "movie or series?"
        )
    )
    return CHOICE

async def name_of_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the movie name!"""
    user = update.message.from_user
    logger.info("User %s chose a %s.", user.first_name, update.message.text)
    await update.message.reply_html(
        text = "What is the name of the movie do you want?",
        reply_markup=ReplyKeyboardRemove()
    )
    return SELECT

async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gives the user movies to select from"""
    logger.info("entering select_movie function in convohandler")
    movies = context.user_data["radarrClient"].search_movie(update.message.text)
    if not movies:
        logger.info("found no search result for %s", update.message.text)
        await update.message.reply_html(
            text="Coulnd find any movies"
        )
        return CHOICE
    
    context.user_data["movies"] = movies
    logger.info("found %s search result for movie %s", len(movies),update.message.text)

    #here i need to implement a prev, next function to scroll through the movies and then select the one!
    index = 0
    keyboard = [
        [
        InlineKeyboardButton(text="select",callback_data= f"select_{index}"),
        InlineKeyboardButton(text="next", callback_data=f"next_{index}"),
        InlineKeyboardButton(text="prev", callback_data=f"prev_{index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        caption=f"{context.user_data["movies"][index]["title"]}, year: {context.user_data["movies"][index]["year"]}",
        photo=movies[index]["images"][0]["remoteUrl"],
        reply_markup= markup
    )

    return MOVIE

async def quality_of_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add the movie to radarr"""
    movie_number = int(update.message.text)
    movie = context.user_data["movies"][movie_number]
    user = update.message.from_user
    context.user_data["radarrClient"].add_movie(title=movie["title"], tmdbId=movie["tmdbId"], rootFolderPath=context.user_data["radarrClient"].rootFolder, qualityProfileId=4)
    logger.info("User %s chose the movie %s.", user.first_name, movie["title"])
    await update.message.reply_html(
        text = "Adding movie"
    )
    await update.message.reply_photo(
        movie["images"][0]["remoteUrl"]
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

if __name__== "__main__":
    application = ApplicationBuilder().token(getToken(token_text)).build()
    
    conv_handler = ConversationHandler(
        entry_points= [CommandHandler('get', entry)],
        states={
            CHOICE: [MessageHandler(filters.Regex("^(movie|series)$"), name_of_movie)],
            SELECT: [MessageHandler(filters.TEXT, select_movie)],
            MOVIE: [MessageHandler(filters.TEXT, quality_of_movie)],
            QUALITY: [MessageHandler(filters.Regex("^(1080p|720p)$"), cancel)]
        },
        fallbacks= [CommandHandler('cancel', cancel)]
    )


    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    help_handler = CommandHandler('help', help)
    caps_handler = CommandHandler('caps', caps)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)


    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(help_handler)
    application.add_handler(caps_handler)
    application.add_handler(CallbackQueryHandler(button))

    #application.add_handler(unknown_handler)
    application.run_polling()