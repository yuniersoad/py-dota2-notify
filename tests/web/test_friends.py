import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dota2_notify.web import friends


def test_get_friends_with_authenticated_user():
    """Test that / endpoint returns friends list for authenticated user"""
    app = FastAPI()
    app.include_router(friends.router)
    
    # Mock get_current_user to return a valid steam_id
    test_steam_id = "76561198012345678"
    
    async def mock_get_current_user():
        return test_steam_id
    
    # Override the dependency
    app.dependency_overrides[friends.get_current_user] = mock_get_current_user
    
    client = TestClient(app)
    
    # Make request to the friends endpoint
    response = client.get("/")
    
    # Assert successful response
    assert response.status_code == 200
    
    # Verify the response contains the steam_id
    assert test_steam_id in response.text
    
    # Verify the response contains the friends
    assert "Friend1" in response.text
    assert "Friend2" in response.text
    assert "Friend3" in response.text
