import httpx

class TelegramClient:
    BASE_URL = "https://api.telegram.org/bot{token}/"

    def __init__(self, token: str, client: httpx.AsyncClient):
        self.client = client
        self.client.base_url = self.BASE_URL.format(token=token)

    async def send_message(self, chat_id: int, text: str) -> dict:
        response = await self.client.post("sendMessage", json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
        return response.json()