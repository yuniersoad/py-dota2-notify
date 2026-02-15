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
        
        
        assert len(response) == 2
        assert response[0] == "76561198098445678"
        assert response[1] == "76561198153901234"


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
        
        assert len(response) == 2
        assert response[0].steamid == "76561198098445678"
        assert response[0].personaname == "Player1"
        assert response[0].profileurl == "https://steamcommunity.com/id/player1/"
        assert response[0].avatar == "https://avatars.steamstatic.com/avatar1.jpg"
        assert response[1].steamid == "76561198153901234"
        assert response[1].personaname == "Player2"
        assert response[1].profileurl == "https://steamcommunity.com/id/player2/"
        assert response[1].avatar == "https://avatars.steamstatic.com/avatar2.jpg"

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

@pytest.mark.asyncio
async def test_validate_auth_request_raises_error(httpx_mock):
    httpx_mock.add_exception(httpx.RequestError("Connection failed"))

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        params = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198882123456"
        }
        result = await steam_client.validate_auth_request(params)
        assert result is False

@pytest.mark.asyncio
async def test_get_match_history_private_profile(httpx_mock):
    body = {
        "result": {
            "status": 15,
            "statusDetail": "Cannot get match history for a user that hasn't allowed it"
        }
    }
    httpx_mock.add_response(
        url="https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v1/?account_id=76561198882123456&key=dummy_key",
        method="GET",
        json=body
    )

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        response, is_public = await steam_client.get_match_history(steam_id="76561198882123456")
        
        assert "result" in response
        assert response["result"]["status"] == 15
        assert response["result"]["statusDetail"] == "Cannot get match history for a user that hasn't allowed it"
        assert is_public is False

@pytest.mark.asyncio
async def test_get_match_history_public_profile(httpx_mock):
    body = {
        "result": {
            "status": 1,
            "num_results": 2,
            "total_results": 2,
            "results_remaining": 0,
            "matches": [
                {
                    "match_id": 7812345678,
                    "match_seq_num": 6543210987,
                    "start_time": 1707494400,
                    "lobby_type": 0,
                    "radiant_team_id": 0,
                    "dire_team_id": 0
                },
                {
                    "match_id": 7812345679,
                    "match_seq_num": 6543210988,
                    "start_time": 1707497000,
                    "lobby_type": 0,
                    "radiant_team_id": 0,
                    "dire_team_id": 0
                }
            ]
        }
    }
    httpx_mock.add_response(
        url="https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v1/?account_id=76561198882123456&key=dummy_key",
        method="GET",
        json=body
    )

    async with httpx.AsyncClient() as client:
        steam_client = SteamClient(api_key="dummy_key", client=client)
        response, is_public = await steam_client.get_match_history(steam_id="76561198882123456")
        
        assert "result" in response
        assert response["result"]["status"] == 1
        assert response["result"]["num_results"] == 2
        assert len(response["result"]["matches"]) == 2
        assert response["result"]["matches"][0]["match_id"] == 7812345678
        assert response["result"]["matches"][1]["match_id"] == 7812345679
        assert is_public is True