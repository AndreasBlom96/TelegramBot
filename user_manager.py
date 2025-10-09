from telegram import Update
from telegram.ext import ContextTypes


VALID_ROLES = ["owner", "admin", "user"]

class UserManager:

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user = update.effective_user
        self.id = update.effective_user.id
        self.context = context

    def get_user_dict(self) -> dict:
        users = self.context.bot_data.get("users", {})
        return users.get(self.id, {})

    def get_role(self) -> str:
        return self.get_user_dict().get("role")
    
    def get_quota(self) -> int:
        return self.get_user_dict().get("quota")

    def edit_role(self, new_role: str) -> bool:

        new_role = new_role.lower()

        # check valid roles
        if new_role not in VALID_ROLES:
            return False

        user_dict = self.get_user_dict()

        if not user_dict:
            return False  # user not found
        
        user_dict["role"] = new_role
        return True
    
    def get_recent_movies(self) -> list:
        return self.context.user_data.get("recent movies", [])