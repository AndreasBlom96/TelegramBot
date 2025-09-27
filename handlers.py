import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler, ConversationHandler, CallbackQueryHandler
import logging
from radarr import RadarrClient
token_text = "config.txt"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

#help functions
def getToken(fileName):
    with open(fileName, "r") as file:
        content = file.readline().strip()
        #print(content)
        return content
    logger.error("Could not open txt file with bot token")
    return None

def get_user(update: Update):
    if update.message:
        return update.message.from_user
    elif update.callback_query:
        return update.callback_query.from_user

#Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! to start asking for a movie, write /movie")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= "Write command /movie to start adding movie")

async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text = text_caps)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text = "Unknown command!")

#messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

#Inline button
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
            caption=f"Nice",
            reply_markup= None
        )
        return await add_movie(update, context)
    elif action == "select":
        context.user_data["selected_index"] = current_index

        keyboard = [
            [
                InlineKeyboardButton(text="yes", callback_data=f"add_{current_index}"),
                InlineKeyboardButton(text="No", callback_data=f"next_-1")
            ]
        ]
        await query.edit_message_caption(
            caption=f"you selected {context.user_data["movies"][current_index]["title"]}. Are you sure?",
            reply_markup= InlineKeyboardMarkup(keyboard)
        )
        return SELECT
    elif action == "movie":
        await query.edit_message_text(
            text= "What movie do you want?",
            reply_markup=None
        )
        return None

    keyboard = [
        [
        InlineKeyboardButton(text="select",callback_data= f"select_{current_index}"),
        InlineKeyboardButton(text="next", callback_data=f"next_{current_index}"),
        InlineKeyboardButton(text="prev", callback_data=f"prev_{current_index}"),
        InlineKeyboardButton(text="cancel", callback_data=f"cancel_{current_index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    default_photo = "https://w7.pngwing.com/pngs/116/765/png-transparent-clapperboard-computer-icons-film-movie-poster-angle-text-logo-thumbnail.png"
    photo_url = default_photo

    movie = context.user_data["movies"][current_index]
    
    if movie["images"]:
        photo_url = movie["images"][0]["remoteUrl"]

    overview = movie["overview"]
    if len(overview) > 100:
        overview[:97] + "..."

    await query.edit_message_media(media=InputMediaPhoto(photo_url))
    await query.edit_message_caption(
        f'{movie["title"]}, year: {movie["year"]} \n\n{movie["overview"]}', 
        reply_markup=markup
        )

#conversations
ENTRY, SELECT = range(2)

async def movie_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of conversation!"""
    logger.info("Entry of conversation")
    r = RadarrClient()
    context.user_data["radarrClient"] = r
    await update.message.reply_html(
        text= "what movie do you want to add?",
        reply_markup= None
    )
    return SELECT

async def select_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gives the user movies to select from"""
    logger.info("entering select_movie function in convohandler")
    movies = context.user_data["radarrClient"].search_movie(update.message.text)
    if not movies:
        logger.info("found no search result for %s", update.message.text)
        await update.message.reply_html(
            text=f"didnt find any movies with query: {update.message.text}"
        )
        return SELECT
    
    context.user_data["movies"] = movies
    logger.info("found %s search result for movie %s", len(movies),update.message.text)

    #here i need to implement a prev, next function to scroll through the movies and then select the one!
    index = 0
    keyboard = [
        [
        InlineKeyboardButton(text="select",callback_data= f"select_{index}"),
        InlineKeyboardButton(text="next", callback_data=f"next_{index}"),
        InlineKeyboardButton(text="prev", callback_data=f"prev_{index}"),
        InlineKeyboardButton(text="cancel", callback_data=f"cancel_{index}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    movie = movies[index]
    overview = movie["overview"]
    if len(overview) > 100:
        overview[:97] + "..."

    await update.message.reply_photo(
        caption=f"{movie["title"]}, year: {movie["year"]} \n\n{overview}",
        photo=movies[index]["images"][0]["remoteUrl"],
        reply_markup= markup
    )

    return ConversationHandler.END

async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add the movie to radarr"""
    movie_number = context.user_data["selected_index"]
    movie = context.user_data["movies"][movie_number]
    user = get_user(update)
    logger.info("User %s chose the movie %s.", user.first_name, movie["title"])

    #check if movie already exist in radarr
    search_result = context.user_data["radarrClient"]._get_added_movies({"tmdbId": movie["tmdbId"]})
    if search_result:
        await update.callback_query.edit_message_caption(
            caption= "Movie already exists!"
        )
    else:
            context.user_data["radarrClient"].add_movie(
                title=movie["title"], 
                tmdbId=movie["tmdbId"], 
                rootFolderPath=context.user_data["radarrClient"].rootFolder, 
                qualityProfileId=4
                )
            await update.callback_query.edit_message_caption(
            caption = "Movie Added!"
        )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = get_user(update)
    logger.info("User %s canceled the conversation.", user.first_name)
    return ConversationHandler.END

if __name__== "__main__":
    application = ApplicationBuilder().token(getToken(token_text)).build()
    
    conv_handler = ConversationHandler(
        entry_points= [CommandHandler('movie', movie_entry)],
        states={
            SELECT: [MessageHandler(filters.TEXT, select_movie)],
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
    #application.add_handler(echo_handler)
    application.add_handler(help_handler)
    application.add_handler(caps_handler)
    application.add_handler(CallbackQueryHandler(button))

    application.add_handler(unknown_handler)
    application.run_polling()