from radarr import RadarrClient
from telegram.ext import ApplicationBuilder
from handlers import (
    conv_handler,
    start_handler,
    help_handler,
    unknown_handler,
    movie_button_handler,
    get_token
)

if __name__ == "__main__":
    application = ApplicationBuilder().token(get_token()).build()
    application.bot_data["radarrClient"] = RadarrClient()

    
    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(movie_button_handler)

    application.add_handler(unknown_handler)
    application.run_polling()