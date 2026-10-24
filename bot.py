from sonarr import SonarrClient
from radarr import RadarrClient
from telegram.ext import ApplicationBuilder
from handlers import (
    movie_conv_handler,
    start_handler,
    help_handler,
    unknown_handler,
    movie_button_handler,
    list_users_handler,
    claim_owner_handler,
    set_role_handler,
    edit_quota_handler,
    notif_handler,
    series_conv_handler,
    series_browse_button,
    series_select_callback,
    series_monitor_callback,
    series_cancel,
    series_special,
    series_add_specific_seasons,
    error_handler,
)
from constants import (
    BOT_TOKEN,
    RADARR_API_KEY,
    RADARR_HOST,
    RADARR_PORT,
    DEFAULT_USERS,
    SONARR_API_KEY,
    SONARR_HOST,
    SONARR_PORT,
)

#search if owner is in default users
owner_id = None
for user in DEFAULT_USERS.keys():
    if DEFAULT_USERS[user]["role"] == "owner":
        owner_id = user   

if __name__ == "__main__":
    print("starting worlds most awesome bot :) ")
    print("Building application....")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    print("done\n")

    print(f"connecting to radarr at: {RADARR_HOST}:{RADARR_PORT}")
    application.bot_data["radarrClient"] = RadarrClient(API_key=RADARR_API_KEY, host=RADARR_HOST, port=RADARR_PORT)
    print("done\n")

    print(f"connecting to sonarr at: {SONARR_HOST}:{SONARR_PORT}")
    application.bot_data["sonarrClient"] = SonarrClient(API_key=SONARR_API_KEY, host=SONARR_HOST, port=SONARR_PORT)
    print("done\n")

    print("Adding default users...")
    application.bot_data["users"] = DEFAULT_USERS
    if owner_id:
        print("Adding owner")
        application.bot_data["owner"] = owner_id
    print("done")

    print("adding handlers....")
    application.add_handler(movie_conv_handler)
    application.add_handler(series_conv_handler)
    application.add_handler(series_monitor_callback)
    application.add_handler(series_browse_button)
    application.add_handler(series_select_callback)
    application.add_handler(series_cancel)
    application.add_handler(series_special)
    application.add_handler(series_add_specific_seasons)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(movie_button_handler)
    application.add_handler(list_users_handler)
    application.add_handler(claim_owner_handler)
    application.add_handler(set_role_handler)
    application.add_handler(edit_quota_handler)
    application.add_handler(notif_handler)
    application.add_error_handler(error_handler)

    application.add_handler(unknown_handler)
    print("done! \nBot is now running")

    application.run_polling()