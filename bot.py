from radarr import RadarrClient, RADARR_HOST, RADARR_PORT, RADARR_API_KEY
from telegram.ext import ApplicationBuilder
from handlers import (
    conv_handler,
    start_handler,
    help_handler,
    unknown_handler,
    movie_button_handler,
    list_users_handler,
    claim_owner_handler,
    set_role_handler,
    BOT_TOKEN
)

if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.bot_data["radarrClient"] = RadarrClient(API_key=RADARR_API_KEY, host=RADARR_HOST, port=RADARR_PORT)

    
    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(movie_button_handler)
    application.add_handler(list_users_handler)
    application.add_handler(claim_owner_handler)
    application.add_handler(set_role_handler)

    application.add_handler(unknown_handler)
    application.run_polling()