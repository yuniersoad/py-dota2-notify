import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dota2_notify.models.user import User
from dota2_notify.app.config import Settings
from dota2_notify.web.notifications import router
from dota2_notify.web.dependencies import get_user_service
from dota2_notify.app.config import get_settings
from dota2_notify.web.auth import get_current_user


@pytest.fixture
def client_with_mocks():
    """Pytest fixture to set up a TestClient with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)

    # Mock steam_client and attach to app state
    mock_steam_client = MagicMock()
    mock_player_summary = MagicMock()
    mock_player_summary.personaname = "TestUser"
    mock_steam_client.get_player_summaries = AsyncMock(return_value=[mock_player_summary])
    app.state.steam_client = mock_steam_client

    # Mock user_service
    mock_user_service = MagicMock()
    mock_user_service.get_user_async = AsyncMock()
    mock_user_service.get_user_id_by_telegram_token_async = AsyncMock()
    mock_user_service.create_telegram_verify_token_async = AsyncMock()
    mock_user_service.update_user_async = AsyncMock()

    async def mock_get_user_service():
        return mock_user_service
        
    app.dependency_overrides[get_user_service] = mock_get_user_service

    # Mock settings
    def get_test_settings():
        return Settings(
            TELEGRAM__BOTTOKEN="fake",
            COSMOSDB__ENDPOINTURI="fake",
            COSMOSDB__PRIMARYKEY="fake",
            COSMOSDB__DATABASENAME="fake",
            COSMOSDB__CONTAINERNAME="fake",
            COSMOSDB__TOKENCONTAINERNAME="fake",
            MATCHCHECK__INTERVALMINUTES=1,
            MATCHCHECK__ENABLED=False,
            STEAM__APIKEY="fake",
            JWT__COOKIES__SECRET="test_secret_key_for_testing"
        )
    app.dependency_overrides[get_settings] = get_test_settings

    # Mock current user
    test_steam_id = "76561198012345678"
    async def mock_get_current_user():
        return test_steam_id
    
    app.dependency_overrides[get_current_user] = mock_get_current_user

    client = TestClient(app)
    
    yield client, mock_user_service, test_steam_id


@pytest.mark.asyncio
async def test_get_notifications_unverified_user_shows_token(client_with_mocks):
    """Test that get_notifications for an unverified user shows instructions and a token."""
    client, mock_user_service, _ = client_with_mocks
    
    test_account_id = 52079950
    test_token = "UNVERIFIED_TOKEN_123"
    
    unverified_user = User.model_validate({
        "user_id": test_account_id,
        "id": str(test_account_id),
        "name": "TestUser",
        "telegram_chat_id": "",
        "telegram_verify_token": test_token
    })
    
    mock_user_service.get_user_async.return_value = unverified_user
    mock_user_service.get_user_id_by_telegram_token_async.return_value = test_account_id
    
    # Make request to the endpoint
    response = client.get("/notifications")

    # Assertions
    assert response.status_code == 200
    response_text = response.text
    
    # Check that the token is in the response
    assert test_token in response_text
    
    # Check that instructions are present
    assert "Open Telegram and search for the bot" in response_text
    assert "start" in response_text
    
    # Check that it shows the user is not verified
    assert "Your Telegram account is not connected." in response_text


@pytest.mark.asyncio
async def test_get_notifications_unverified_user_regenerates_token(client_with_mocks):
    """Test that get_notifications regenerates a token if the existing one is invalid."""
    client, mock_user_service, _ = client_with_mocks
    
    test_account_id = 52079950
    old_token = "OLD_INVALID_TOKEN"
    new_token = "NEW_VALID_TOKEN"
    
    unverified_user = User.model_validate({
        "user_id": test_account_id,
        "id": str(test_account_id),
        "name": "TestUser",
        "telegram_chat_id": "",
        "telegram_verify_token": old_token
    })
    
    mock_user_service.get_user_async.return_value = unverified_user
    # Simulate that the old token is invalid
    mock_user_service.get_user_id_by_telegram_token_async.return_value = None
    mock_user_service.create_telegram_verify_token_async.return_value = new_token

    # Make request to the endpoint
    response = client.get("/notifications")

    # Assertions
    assert response.status_code == 200
    response_text = response.text
    
    # Check that the new token is in the response and the old one is not
    assert new_token in response_text
    assert old_token not in response_text
    
    # Verify that the token was regenerated and the user updated
    mock_user_service.get_user_id_by_telegram_token_async.assert_called_once_with(old_token)
    mock_user_service.create_telegram_verify_token_async.assert_called_once_with(test_account_id)
    mock_user_service.update_user_async.assert_called_once()
    
    # Check that instructions are present
    assert "Open Telegram and search for the bot" in response_text
    assert "start" in response_text
    assert new_token in response_text


def test_get_notifications_unauthenticated_redirects_to_home():
    """Test that get_notifications redirects to / when no user is logged in."""
    app = FastAPI()
    app.include_router(router)

    async def mock_get_current_user():
        return None

    async def mock_get_user_service():
        return MagicMock()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_user_service] = mock_get_user_service

    client = TestClient(app)
    response = client.get("/notifications/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
