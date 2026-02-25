from pydantic import BaseModel


class SteamPlayerSummary(BaseModel):
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
