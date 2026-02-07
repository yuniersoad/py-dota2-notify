from dataclasses import dataclass


@dataclass
class SteamPlayerSummary:
    """Represents a Steam player summary from the Steam API."""
    steamid: str = ""
    communityvisibilitystate: int = 0
    profilestate: int = 0
    personaname: str = ""
    profileurl: str = ""
    avatar: str = ""
    avatarmedium: str = ""
    avatarfull: str = ""
    avatarhash: str = ""
    lastlogoff: int = 0
    personastate: int = 0
    primaryclanid: str = ""
    timecreated: int = 0
    personastateflags: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "steamid": self.steamid,
            "communityvisibilitystate": self.communityvisibilitystate,
            "profilestate": self.profilestate,
            "personaname": self.personaname,
            "profileurl": self.profileurl,
            "avatar": self.avatar,
            "avatarmedium": self.avatarmedium,
            "avatarfull": self.avatarfull,
            "avatarhash": self.avatarhash,
            "lastlogoff": self.lastlogoff,
            "personastate": self.personastate,
            "primaryclanid": self.primaryclanid,
            "timecreated": self.timecreated,
            "personastateflags": self.personastateflags
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SteamPlayerSummary":
        """Create instance from dictionary (Steam API deserialization)."""
        return cls(
            steamid=data.get("steamid", ""),
            communityvisibilitystate=data.get("communityvisibilitystate", 0),
            profilestate=data.get("profilestate", 0),
            personaname=data.get("personaname", ""),
            profileurl=data.get("profileurl", ""),
            avatar=data.get("avatar", ""),
            avatarmedium=data.get("avatarmedium", ""),
            avatarfull=data.get("avatarfull", ""),
            avatarhash=data.get("avatarhash", ""),
            lastlogoff=data.get("lastlogoff", 0),
            personastate=data.get("personastate", 0),
            primaryclanid=data.get("primaryclanid", ""),
            timecreated=data.get("timecreated", 0),
            personastateflags=data.get("personastateflags", 0)
        )
