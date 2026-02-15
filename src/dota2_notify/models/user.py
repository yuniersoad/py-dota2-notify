from dataclasses import dataclass, field

STEAM_ID_OFFSET = 76561197960265728

def steam_id_to_account_id(steam_id: int) -> int:
    return steam_id - STEAM_ID_OFFSET

def account_id_to_steam_id(account_id: int) -> int:
    return account_id + STEAM_ID_OFFSET

@dataclass
class Friend:
    """Represents a friend in the Dota 2 notification system."""
    id: str = ""
    user_id: int = 0
    name: str = ""
    last_match_id: int = 0
    following: bool = False
    type: str = "friend"

    def to_dict(self) -> dict:
        """Convert to dictionary for Cosmos DB serialization."""
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "lastMatchId": self.last_match_id,
            "following": self.following,
            "type": self.type
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Friend":
        """Create instance from dictionary (Cosmos DB deserialization)."""
        return cls(
            id=data.get("id", ""),
            user_id=data.get("userId", 0),
            name=data.get("name", ""),
            last_match_id=data.get("lastMatchId", 0),
            following=data.get("following", False),
            type=data.get("type", "friend")
        )



@dataclass
class User:
    """Represents a user in the Dota 2 notification system."""
    id: str = ""
    user_id: int = 0
    name: str = ""
    telegram_chat_id: str = ""
    following: bool = True
    last_match_id: int = 0
    type: str = "user"

    def to_dict(self) -> dict:
        """Convert to dictionary for Cosmos DB serialization."""
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "telegramChatId": self.telegram_chat_id,
            "type": self.type,
            "following": self.following,
            "lastMatchId": self.last_match_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create instance from dictionary (Cosmos DB deserialization)."""
        return cls(
            id=data.get("id", ""),
            user_id=data.get("userId", 0),
            name=data.get("name", ""),
            telegram_chat_id=data.get("telegramChatId", ""),
            following=data.get("following", True),
            type=data.get("type", "user"),
            last_match_id=data.get("lastMatchId", 0)
        )
