import httpx
from dota2_notify.models.match import DotaMatch

class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api/"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.client.base_url = self.BASE_URL

    async def get_player_matches(self, account_id: int, limit: int = 10) -> list['DotaMatch']:        
        response = await self.client.get(f"players/{account_id}/matches", params={"limit": limit})
        response.raise_for_status()
        matches_data = response.json()
        
        return [DotaMatch.from_dict(match) for match in matches_data]