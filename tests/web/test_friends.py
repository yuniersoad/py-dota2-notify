import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dota2_notify.web import friends
from unittest.mock import AsyncMock, MagicMock
from dota2_notify.models.steam_player_summary import SteamPlayerSummary
from dota2_notify.models.user import Friend

STEAM_ID_OFFSET = 76561197960265728

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
    # Configure steam_id_to_account_id
    mock_user_service.steam_id_to_account_id = lambda sid: sid - STEAM_ID_OFFSET

    # Create a friend that is being followed (Friend1)
    friend1_steam_id = 76561198111111111
    friend1_account_id = friend1_steam_id - STEAM_ID_OFFSET
    
    followed_friend = Friend(
        id=str(friend1_account_id),
        user_id=int(test_steam_id) - STEAM_ID_OFFSET,
        name="Friend1",
        last_match_id=12345,
        following=True,
        type="friend"
    )

    mock_user_service.get_friends_async = AsyncMock(
        return_value=[followed_friend]
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
    assert "Follow" in response.text
    assert "Unfollow" in response.text


def test_follow_friend_happy_path_new_friend():
    """Test following a friend that is not yet in the database (happy path)"""
    app = FastAPI()
    app.include_router(friends.router)
    
    test_steam_id = "76561198012345678"
    friend_steam_id = "76561198111111111"
    

    async def mock_get_current_user():
        return test_steam_id

    # Mock user_service
    mock_user_service = MagicMock()
    # Mock finding friend in DB returns None (create new friend path)
    mock_user_service.get_friend_by_steam_id_async = AsyncMock(return_value=None)
    mock_user_service.steam_id_to_account_id = lambda sid: sid - STEAM_ID_OFFSET
    mock_user_service.update_friend_async = AsyncMock()

    # Mock steam_client
    mock_steam_client = MagicMock()
    # Friend is in the steam friend list
    mock_steam_client.get_friend_list = AsyncMock(return_value=[friend_steam_id])
    
    mock_steam_client.get_player_summaries = AsyncMock(
        return_value=[
            SteamPlayerSummary(
                steamid=friend_steam_id,
                personaname="New Friend",
                avatar="avatar_url",
                avatarmedium="medium",
                avatarfull="full"
            )
        ]
    )
    # Mock match history for last_match_id, returns (data, is_public)
    mock_steam_client.get_match_history = AsyncMock(
        return_value=({"result": {"matches": [{"match_id": 123456789}]}}, True)
    )

    app.state.user_service = mock_user_service
    app.state.steam_client = mock_steam_client
    app.dependency_overrides[friends.get_current_user] = mock_get_current_user

    client = TestClient(app)
    
    # Perform the POST request to follow the friend
    response = client.post(f"/follow/{friend_steam_id}", follow_redirects=False)

    # Should redirect to home page
    assert response.status_code == 303
    assert response.headers["location"] == "/" # check redirection

    # Check update_friend_async was called with correct data
    mock_user_service.update_friend_async.assert_awaited_once()
    saved_friend = mock_user_service.update_friend_async.call_args[0][0]
    
    assert saved_friend.user_id == int(test_steam_id) - STEAM_ID_OFFSET
    assert saved_friend.id == str(int(friend_steam_id) - STEAM_ID_OFFSET)
    assert saved_friend.name == "New Friend"
    assert saved_friend.last_match_id == 123456789
    assert saved_friend.following is True


def test_unfollow_friend_happy_path():
    """Test unfollowing a friend (happy path)"""
    app = FastAPI()
    app.include_router(friends.router)
    
    test_steam_id = "76561198012345678"
    friend_steam_id = "76561198111111111"

    async def mock_get_current_user():
        return test_steam_id

    # Mock user_service
    mock_user_service = MagicMock()
    
    # Existing friend that is being followed
    friend_account_id = int(friend_steam_id) - STEAM_ID_OFFSET
    existing_friend = Friend(
        id=str(friend_account_id),
        user_id=int(test_steam_id) - STEAM_ID_OFFSET,
        name="Friend To Unfollow",
        last_match_id=12345,
        following=True,
        type="friend"
    )
    
    mock_user_service.get_friend_by_steam_id_async = AsyncMock(return_value=existing_friend)
    mock_user_service.update_friend_async = AsyncMock()

    app.state.user_service = mock_user_service
    app.state.steam_client = MagicMock()
    app.dependency_overrides[friends.get_current_user] = mock_get_current_user

    client = TestClient(app)
    
    # Perform the POST request to unfollow the friend
    response = client.post(f"/unfollow/{friend_steam_id}", follow_redirects=False)

    # Should redirect to home page
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Check update_friend_async was called
    mock_user_service.update_friend_async.assert_awaited_once()
    updated_friend = mock_user_service.update_friend_async.call_args[0][0]
    
    assert updated_friend.id == str(friend_account_id)
    assert updated_friend.following is False
