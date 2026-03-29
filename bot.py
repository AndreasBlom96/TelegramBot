from radarr import RadarrClient
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
    edit_quota_handler,
    notif_handler,
)
from constants import (
    BOT_TOKEN,
    RADARR_API_KEY,
    RADARR_HOST,
    RADARR_PORT
)

if __name__ == "__main__":
    print("starting worlds most awesome bot :) ")
    print("Builing application....")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    print("done\n")

    print("connecting to radarr...")
    application.bot_data["radarrClient"] = RadarrClient(API_key=RADARR_API_KEY, host=RADARR_HOST, port=RADARR_PORT)
    print("done\n")

    print("adding handlers....")
    application.add_handler(conv_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(movie_button_handler)
    application.add_handler(list_users_handler)
    application.add_handler(claim_owner_handler)
    application.add_handler(set_role_handler)
    application.add_handler(edit_quota_handler)
    application.add_handler(notif_handler)

    application.add_handler(unknown_handler)
    print("done! \nBot is now running")

    application.run_polling()