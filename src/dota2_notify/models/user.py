from pydantic import BaseModel, Field, ConfigDict

STEAM_ID_OFFSET = 76561197960265728


def steam_id_to_account_id(steam_id: int) -> int:
    return steam_id - STEAM_ID_OFFSET


def account_id_to_steam_id(account_id: int) -> int:
    return account_id + STEAM_ID_OFFSET


class Friend(BaseModel):
    """Represents a friend in the Dota 2 notification system."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    id: str = ""
    user_id: int = Field(0, alias="userId")
    name: str = ""
    following: bool = False
    type: str = "friend"


class User(BaseModel):
    """Represents a user in the Dota 2 notification system."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    id: str = ""
    user_id: int = Field(0, alias="userId")
    name: str = ""
    telegram_chat_id: str = Field("", alias="telegramChatId")
    telegram_username: str = Field("", alias="telegramUsername")
    telegram_verify_token: str = Field("", alias="telegramVerifyToken")
    following: bool = True
    type: str = "user"

    @property
    def is_telegram_verified(self) -> bool:
        """Check if the user has a verified Telegram chat ID."""
        return bool(self.telegram_chat_id and self.telegram_chat_id.strip())


class UserTelegramVerifyToken(BaseModel):
    """Represents a Telegram verification token for a user."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    id: str = ""
    user_id: int = Field(0, alias="userId")
    token: str = ""
    type: str = "telegram_verify_token"
    # To enable TTL in Cosmos DB, you need to enable it on the container.
    # The `_ttl` property will be used by Cosmos DB to automatically delete the document.
    ttl: int = Field(7*24*60*60, alias="ttl")  # 1 week in seconds