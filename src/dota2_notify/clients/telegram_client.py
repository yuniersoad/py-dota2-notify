import httpx

class TelegramClient:
    BASE_URL_TEMPLATE = "https://api.telegram.org/bot{token}/"

    def __init__(self, token: str, client: httpx.AsyncClient):
        self.client = client
        self.base_url = self.BASE_URL_TEMPLATE.format(token=token)

    async def send_message(self, chat_id: int, text: str) -> dict:
        response = await self.client.post(f"{self.base_url}sendMessage", json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
        return response.json()