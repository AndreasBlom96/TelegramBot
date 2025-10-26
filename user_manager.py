from telegram import Update
from telegram.ext import ContextTypes
from constants import DEFAULT_QUOTA
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

VALID_ROLES = ["owner", "admin", "user"]

class UserManager:

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user = update.effective_user
        self.id = update.effective_user.id
        self.context = context
        self.update = update

    
    def required_roles(*roles):
        def decorator(func):
            async def wrapper_required_roles(*args,**kwargs):
                self = args[0]
                if self.get_role() not in roles:
                    logger.warning(
                        "you do not have the rights for this operation"
                        )
                    await self.update.message.reply_html(
                        text="You do not have the rights"
                        )
                    return

                return await func(*args, **kwargs)
            return wrapper_required_roles
        return decorator


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

    @required_roles("owner", "admin")
    async def set_quota(self, target_id: int=None, new_quota: int=0):
        """sets new quota for users"""
        if new_quota < 0:
            new_quota = 0

        user_dict = self.get_user_dict(target_id)
        user_dict["quota"] = new_quota


    @required_roles("owner")
    async def edit_role(self, new_role: str, target_id: int=None) -> bool:
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
        # update recent movie list
        current_list = self.context.user_data.get("recent movies", [])
        limit = datetime.now() - timedelta(days=7)
        new_list = [t for t in current_list if t[1] > limit]
        self.context.user_data["recent movies"] = new_list

        return new_list
    

    def add_user(self) -> None:
        """Adds user to bot_data users list"""
        users = self.context.bot_data.setdefault("users", {})

        # Add to list of users
        if self.id not in users:
            logger.info(f"adding user: {self.user.full_name} to list of users")
            self.context.bot_data["users"].setdefault(self.id, {
            "role": "user",
            "username": self.user.username,
            "name": self.user.full_name,
            "quota": DEFAULT_QUOTA
            }) 


    def isOwner(self, target_id: int=None) -> bool:
        """returns true if user is bot owner"""
        if self.get_role(target_id) == "owner":
            return True
        return False
    
    
    async def met_quota(self) -> bool:
        """Check if weekly movie quotas is met. Returns true if met"""

        recent_movies = self.get_recent_movies()
        quota = self.get_quota()
        if len(recent_movies) >= quota and self.get_role() == "user":
            logger.info(f"User has met their weekly quota of {quota} movies. Aborting")
            await self.update.message.reply_html(text=f"Your weekly quota of {quota} has been met. \
            You have to wait before adding another movie")
            return True
        return False
    
