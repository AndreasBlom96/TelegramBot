import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler, ConversationHandler
import logging
import requests
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
        content = file.readline()
        #print(content)
        return content

#Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= "you need help????")

async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text = text_caps)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text = "Unknown command!")

#messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(text = "i can echo your messages!")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


#conversations
CHOICE, MOVIE, QUALITY = range(3)
async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry of conversation!"""
    reply_keyboard = [["movie", "series", "cancel"]]
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
    return MOVIE

async def quality_of_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the movie quality"""
    reply_keyboard = [["1080p", "720p", "Doesnt matter"]]
    user = update.message.from_user
    logger.info("User %s chose the movie %s.", user.first_name, update.message.text)
    await update.message.reply_html(
        text = "What quality?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Pick quality"
        )
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
    
    conv_handler = ConversationHandler(g
        entry_points= [CommandHandler('get', entry)],
        states={
            CHOICE: [MessageHandler(filters.Regex("^(movie|series)$"), name_of_movie)],
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

    #application.add_handler(unknown_handler)
    application.run_polling()