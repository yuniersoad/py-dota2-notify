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
    last_match_id: int = Field(0, alias="lastMatchId")
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
    last_match_id: int = Field(0, alias="lastMatchId")
    type: str = "user"

    @property
    def is_telegram_verified(self) -> bool:
        """Check if the user has a verified Telegram chat ID."""
        return bool(self.telegram_chat_id and self.telegram_chat_id.strip())


class UserTelegramVerifyToken(BaseModel):
    """Represents a Telegram verification token for a user."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    # TODO: make the token temporary with a cosmos db TTL
    id: str = ""
    user_id: int = Field(0, alias="userId")
    token: str = ""
    type: str = "telegram_verify_token"