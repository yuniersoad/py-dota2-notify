import httpx

class SteamClient:
    BASE_URL = "https://api.steampowered.com/"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self.api_key = api_key
        self.client = client
        self.client.base_url = self.BASE_URL

    async def get_player_summaries(self, steam_ids: list[str]) -> dict:
        response = await self.client.get(
            "ISteamUser/GetPlayerSummaries/v2/",
            params={"steamids": ",".join(steam_ids), "key": self.api_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_friend_list(self, steam_id: str) -> dict:
        response = await self.client.get(
            "ISteamUser/GetFriendList/v1/",
            params={"steamid": steam_id, "key": self.api_key, "relationship": "friend"}
        )
        response.raise_for_status()
        return response.json()