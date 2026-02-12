import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dota2_notify.web import friends
from unittest.mock import AsyncMock, MagicMock
from dota2_notify.models.steam_player_summary import SteamPlayerSummary


def test_get_friends_with_authenticated_user():
    """Test that / endpoint returns friends list for authenticated user"""
    app = FastAPI()
    app.include_router(friends.router)
    
    # Mock get_current_user to return a valid steam_id
    test_steam_id = "76561198012345678"
    
    async def mock_get_current_user():
        return test_steam_id
    
    # Mock user_service
    
    mock_user_service = MagicMock()
    mock_user_service.get_user_with_steam_id_async = AsyncMock(
        return_value={"steam_id": int(test_steam_id), "name": "TestUser"}
    )
    mock_user_service.get_friends_async = AsyncMock(
        return_value=[]
    )
    
    # Mock steam_client
    mock_steam_client = MagicMock()
    mock_steam_client.get_friend_list = AsyncMock(return_value=["76561198111111111", "76561198222222222", "76561198333333333"])

    mock_steam_client.get_player_summaries = AsyncMock(
        return_value=[
            SteamPlayerSummary(
                steamid="76561198111111111",
                personaname="Friend1",
                avatar="https://avatar.example.com/friend1.jpg",
                avatarmedium="https://avatar.example.com/friend1_medium.jpg",
                avatarfull="https://avatar.example.com/friend1_full.jpg"
            ),
            SteamPlayerSummary(
                steamid="76561198222222222",
                personaname="Friend2",
                avatar="https://avatar.example.com/friend2.jpg",
                avatarmedium="https://avatar.example.com/friend2_medium.jpg",
                avatarfull="https://avatar.example.com/friend2_full.jpg"
            ),
            SteamPlayerSummary(
                steamid="76561198333333333",
                personaname="Friend3",
                avatar="https://avatar.example.com/friend3.jpg",
                avatarmedium="https://avatar.example.com/friend3_medium.jpg",
                avatarfull="https://avatar.example.com/friend3_full.jpg"
            )
        ]
    )
    
    # Set up app state with mocked services
    app.state.user_service = mock_user_service
    app.state.steam_client = mock_steam_client
    
    
    # Override the dependency
    app.dependency_overrides[friends.get_current_user] = mock_get_current_user
    
    client = TestClient(app)
    
    # Make request to the friends endpoint
    response = client.get("/")
    
    # Assert successful response
    assert response.status_code == 200
    
    # Verify the response contains the steam_id
    assert "TestUser" in response.text
    
    # Verify the response contains the friends
    assert "Friend1" in response.text
    assert "Friend2" in response.text
    assert "Friend3" in response.text
