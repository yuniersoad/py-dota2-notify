import json
import pytest
from dota2_notify.clients.opendota_client import OpenDotaClient
import httpx

@pytest.mark.asyncio
async def test_with_fixture(httpx_mock):
    body = """[
    {
        "match_id": 8645865856,
        "player_slot": 132,
        "radiant_win": true,
        "duration": 2359,
        "game_mode": 22,
        "lobby_type": 7,
        "hero_id": 112,
        "start_time": 1768176773,
        "version": null,
        "kills": 5,
        "deaths": 14,
        "assists": 14,
        "average_rank": 42,
        "leaver_status": 0,
        "party_size": null,
        "hero_variant": 3
    },
    {
        "match_id": 8645838603,
        "player_slot": 129,
        "radiant_win": false,
        "duration": 2107,
        "game_mode": 22,
        "lobby_type": 7,
        "hero_id": 155,
        "start_time": 1768173913,
        "version": null,
        "kills": 4,
        "deaths": 5,
        "assists": 18,
        "average_rank": 42,
        "leaver_status": 0,
        "party_size": 1,
        "hero_variant": 3
    }
]"""
    httpx_mock.add_response(url="https://api.opendota.com/api/players/192852394/matches?limit=2", json=json.loads(body))
    
    async with httpx.AsyncClient() as client:
        dota_client = OpenDotaClient(client)
        response = await dota_client.get_player_matches(account_id=192852394, limit=2)
        assert len(response) == 2
        assert response[0].match_id == 8645865856
        assert response[1].match_id == 8645838603
        assert response[0].hero_name == "Winter Wyvern"
        assert response[1].hero_name == "Largo"
        assert response[0].player_won == False
        assert response[1].player_won == True