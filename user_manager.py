from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

VALID_ROLES = ["owner", "admin", "user"]

class UserManager:

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user = update.effective_user
        self.id = update.effective_user.id
        self.context = context

    def get_user_dict(self, target_id: int=None) -> dict:
        """Resturns the users dict from context.bot_data"""
        if target_id:
            user_id = target_id
        else:
            user_id = self.id

        users = self.context.bot_data.get("users", {})
        return users.get(user_id, {})


    def get_role(self, target_id: int=None) -> str:
        """returns users role"""
        return self.get_user_dict(target_id).get("role")
    

    def get_quota(self) -> int:
        """returns """
        return self.get_user_dict().get("quota")


    def set_quota(self, target_id: int=None, new_quota: int=0):
        """sets new quota users"""
        if new_quota < 0:
            new_quota = 0
        user_dict =  self.get_user_dict(target_id)["quota"]
        user_dict["quota"] = new_quota


    def edit_role(self, new_role: str, target_id: int=None) -> bool:
        """edits role for user"""
        new_role = new_role.lower()

        # check valid roles
        if new_role not in VALID_ROLES:
            logger.warning("not a valid role")
            return False

        user_dict = self.get_user_dict(target_id)

        if (not user_dict) or (user_dict.get("role") == "owner"):
            logger.warning(f"failed to set new role")
            return False  # user not found

        user_dict["role"] = new_role
        logger.info(f"new role {new_role} set for user {user_dict.get("name")}")
        return True
    

    def get_recent_movies(self) -> list:
        """returns list of recent movies"""
        return self.context.user_data.get("recent movies", [])
    

    def isOwner(self, target_id: int=None) -> bool:
        """returns true if user is bot owner"""
        if self.get_role(target_id) == "owner":
            return True
        return False