from urllib import response
import httpx

from ..models.steam_player_summary import SteamPlayerSummary 

class SteamClient:
    BASE_URL = "https://api.steampowered.com/"
    OPEN_ID_URL = "https://steamcommunity.com/openid/login"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self.api_key = api_key
        self.client = client
        
    async def validate_auth_request(self, params: dict) -> bool:         
        params["openid.mode"] = "check_authentication"
        try:
            response = await self.client.post(self.OPEN_ID_URL, data=params)
        except httpx.HTTPError:
            return False
        return "is_valid:true" in response.text

    async def get_player_summaries(self, steam_ids: list[str]) -> list[SteamPlayerSummary]:
        response = await self.client.get(
            f"{self.BASE_URL}ISteamUser/GetPlayerSummaries/v2/",
            params={"steamids": ",".join(steam_ids), "key": self.api_key}
        )
        response.raise_for_status()
        data = response.json()
        players_data = data.get("response", {}).get("players", [])
        return [SteamPlayerSummary.from_dict(player) for player in players_data]
    
    async def get_friend_list(self, steam_id: str) -> dict:
        response = await self.client.get(
            f"{self.BASE_URL}ISteamUser/GetFriendList/v1/",
            params={"steamid": steam_id, "key": self.api_key, "relationship": "friend"}
        )
        response.raise_for_status()
        return response.json()