from radarr import RadarrClient, RADARR_HOST, RADARR_PORT
from telegram.ext import ApplicationBuilder
from handlers import (
    conv_handler,
    start_handler,
    help_handler,
    unknown_handler,
    movie_button_handler,
    BOT_TOKEN
)

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.bot_data["radarrClient"] = RadarrClient(host=RADARR_HOST, port=RADARR_PORT)

    
    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(movie_button_handler)

    application.add_handler(unknown_handler)
    application.run_polling()