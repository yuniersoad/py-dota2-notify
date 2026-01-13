import pytest
import json
import httpx
from dota2_notify.clients.telegram_client import TelegramClient
    


@pytest.mark.asyncio
async def test_with_fixture(httpx_mock):
    response_body = {'ok': True, 'result': {'message_id': 1117, 'from': {'id': 7630007362, 'is_bot': True, 'first_name': 'dota_notify_bot', 'username': 'my_bot'}, 'chat': {'id': 242351866, 'first_name': 'Y', 'last_name': 'P', 'username': 'username', 'type': 'private'}, 'date': 1768329812, 'text': 'que fue'}}
    
    httpx_mock.add_response(url="https://api.telegram.org/botTEST_TOKEN/sendMessage", method="POST", json=response_body)
    async with httpx.AsyncClient() as client:
        telegram_client = TelegramClient(token="TEST_TOKEN", client=client)
        
        response = await telegram_client.send_message(chat_id=242351866, text="que fue")
        
        assert response['ok'] is True
        request = httpx_mock.get_request()
        sent_data = json.loads(request.read())
        assert sent_data == {'chat_id': 242351866, 'text': 'que fue'}
        assert request.method == "POST"