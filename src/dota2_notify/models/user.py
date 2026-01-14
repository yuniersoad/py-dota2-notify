from dataclasses import dataclass, field
from typing import List


@dataclass
class FollowedPlayer:
    """Represents a player being followed by a user."""
    user_id: int = 0
    name: str = ""
    last_match_id: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for Cosmos DB serialization."""
        return {
            "userId": self.user_id,
            "name": self.name,
            "lastMatchId": self.last_match_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FollowedPlayer":
        """Create instance from dictionary (Cosmos DB deserialization)."""
        return cls(
            user_id=data.get("userId", 0),
            name=data.get("name", ""),
            last_match_id=data.get("lastMatchId", 0)
        )


@dataclass
class User:
    """Represents a user in the Dota 2 notification system."""
    id: str = ""
    user_id: int = 0
    name: str = ""
    telegram_chat_id: str = ""
    following: List[FollowedPlayer] = field(default_factory=list)
    type: str = "user"

    def to_dict(self) -> dict:
        """Convert to dictionary for Cosmos DB serialization."""
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "telegramChatId": self.telegram_chat_id,
            "following": [player.to_dict() for player in self.following],
            "type": self.type
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create instance from dictionary (Cosmos DB deserialization)."""
        return cls(
            id=data.get("id", ""),
            user_id=data.get("userId", 0),
            name=data.get("name", ""),
            telegram_chat_id=data.get("telegramChatId", ""),
            following=[
                FollowedPlayer.from_dict(player) 
                for player in data.get("following", [])
            ],
            type=data.get("type", "user")
        )