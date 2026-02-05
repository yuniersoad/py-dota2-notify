import json
import pytest
import httpx

from dota2_notify.clients.steam_client import SteamClient

@pytest.mark.asyncio
async def test_get_friends(httpx_mock):
    body = """{
    "friendslist": {
        "friends": [
            {
                "steamid": "76561198098445678",
                "relationship": "friend",
                "friend_since": 1546568438
            },
            {
                "steamid": "76561198153901234",
                "relationship": "friend",
                "friend_since": 1546295859
            }]
            }
            }
            """
    httpx_mock.add_response(url="https://api.steampowered.com/ISteamUser/GetFriendList/v1/?key=dummy_key&steamid=76561198882123456&relationship=friend", method="GET", json=json.loads(body))

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        response = await steam_client.get_friend_list(steam_id="76561198882123456")
        
        assert "friendslist" in response
        assert len(response["friendslist"]["friends"]) == 2
        assert response["friendslist"]["friends"][0]["steamid"] == "76561198098445678"
        assert response["friendslist"]["friends"][1]["steamid"] == "76561198153901234"


@pytest.mark.asyncio
async def test_get_player_summaries(httpx_mock):
    body = {
        "response": {
            "players": [
                {
                    "steamid": "76561198098445678",
                    "personaname": "Player1",
                    "profileurl": "https://steamcommunity.com/id/player1/",
                    "avatar": "https://avatars.steamstatic.com/avatar1.jpg"
                },
                {
                    "steamid": "76561198153901234",
                    "personaname": "Player2",
                    "profileurl": "https://steamcommunity.com/id/player2/",
                    "avatar": "https://avatars.steamstatic.com/avatar2.jpg"
                }
            ]
        }
    }
    httpx_mock.add_response(
        url="https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=dummy_key&steamids=76561198098445678%2C76561198153901234",
        method="GET",
        json=body
    )

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        response = await steam_client.get_player_summaries(steam_ids=["76561198098445678", "76561198153901234"])
        
        assert "response" in response
        assert "players" in response["response"]
        assert len(response["response"]["players"]) == 2
        assert response["response"]["players"][0]["steamid"] == "76561198098445678"
        assert response["response"]["players"][0]["personaname"] == "Player1"


@pytest.mark.asyncio
async def test_validate_auth_request(httpx_mock):
    httpx_mock.add_response(
        url="https://steamcommunity.com/openid/login",
        method="POST",
        text="is_valid:true\n"
    )

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        params = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198882123456"
        }
        result = await steam_client.validate_auth_request(params)
        
        assert result is True