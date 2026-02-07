import pytest
import os
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from dota2_notify.models.user import User
from dota2_notify.web.auth import router, cookie_name, get_current_user, create_access_token
from urllib.parse import parse_qs, urlparse
from jose import jwt


def test_login_redirects_to_steam_openid():
    """Test that /login endpoint redirects to Steam OpenID with correct parameters"""
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    
    # Make request to login endpoint
    response = client.get("/auth/login", follow_redirects=False)
    
    # Assert it's a redirect
    assert response.status_code == 307
    
    # Parse the redirect URL
    redirect_url = response.headers["location"]
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    
    # Verify redirect goes to Steam OpenID
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "steamcommunity.com"
    assert parsed_url.path == "/openid/login"
    
    # Verify OpenID parameters are correct
    assert query_params["openid.ns"][0] == "http://specs.openid.net/auth/2.0"
    assert query_params["openid.mode"][0] == "checkid_setup"
    assert query_params["openid.identity"][0] == "http://specs.openid.net/auth/2.0/identifier_select"
    assert query_params["openid.claimed_id"][0] == "http://specs.openid.net/auth/2.0/identifier_select"
    
    # Verify callback URLs include the test client's base URL
    assert "http://testserver/auth/steam/callback" in query_params["openid.return_to"][0]
    assert "http://testserver/" in query_params["openid.realm"][0]


@pytest.mark.asyncio
async def test_steam_callback_sets_jwt_cookie(monkeypatch):
    """Test that /steam/callback validates, extracts Steam ID, and sets a JWT cookie"""
    # Set up test JWT secret by patching the module variable
    test_jwt_secret = "test_secret_key_for_testing"
    
    # Import auth module to patch its jwt_secret_key
    from dota2_notify.web import auth
    monkeypatch.setattr(auth, "jwt_secret_key", test_jwt_secret)
    
    # Create app and add mocked steam_client to app state
    app = FastAPI()
    app.include_router(router)
    
    # Mock the steam_client's validate_auth_request method
    mock_steam_client = MagicMock()
    mock_steam_client.validate_auth_request = AsyncMock(return_value=True)
    app.state.steam_client = mock_steam_client

    # mock the user_service assume the user does already exist
    mock_user_service = MagicMock()
    mock_user_service.get_user_with_steam_id_async = AsyncMock(return_value=User.from_dict({"user_id": 52079950, "id": "52079950", "name": "TestUser"}))
    app.state.user_service = mock_user_service  
    
    client = TestClient(app)
    
    # Test Steam ID
    test_steam_id = "76561198012345678"
    
    # Build query parameters that Steam would send
    query_params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "id_res",
        "openid.claimed_id": f"https://steamcommunity.com/openid/id/{test_steam_id}",
        "openid.identity": f"https://steamcommunity.com/openid/id/{test_steam_id}",
    }
    
    # Make request to callback endpoint
    response = client.get("/auth/steam/callback", params=query_params, follow_redirects=False)
    
    # Assert it's a redirect to home
    assert response.status_code == 307
    assert response.headers["location"] == "/"
    
    # Verify the cookie is set
    assert cookie_name in response.cookies
    token = response.cookies[cookie_name]
    
    # Decode and verify the JWT
    payload = jwt.decode(token, test_jwt_secret, algorithms=["HS256"])
    
    # Verify Steam ID is in the token
    assert payload["sub"] == test_steam_id
    
    # Verify token has expiration
    assert "exp" in payload
    
    # Verify the steam_client.validate_auth_request was called
    mock_steam_client.validate_auth_request.assert_called_once()


@pytest.mark.asyncio
async def test_steam_callback_rejects_invalid_validation():
    """Test that /steam/callback returns 400 when validation fails"""
    # Create app and add mocked steam_client to app state
    app = FastAPI()
    app.include_router(router)
    
    # Mock the steam_client's validate_auth_request method to return False
    mock_steam_client = MagicMock()
    mock_steam_client.validate_auth_request = AsyncMock(return_value=False)
    app.state.steam_client = mock_steam_client
    
    client = TestClient(app)
    
    # Build query parameters (doesn't matter what they are since validation will fail)
    query_params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "id_res",
        "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198012345678",
        "openid.identity": "https://steamcommunity.com/openid/id/76561198012345678",
    }
    
    # Make request to callback endpoint
    response = client.get("/auth/steam/callback", params=query_params)
    
    # Assert it returns 400 Bad Request
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Steam login"}
    
    # Verify the cookie is NOT set
    assert cookie_name not in response.cookies
    
    # Verify the steam_client.validate_auth_request was called
    mock_steam_client.validate_auth_request.assert_called_once()


def test_logout_clears_cookie_and_redirects():
    """Test that /logout clears the auth cookie and redirects to home"""
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    
    # Set a cookie to simulate a logged-in user
    client.cookies.set(cookie_name, "fake_jwt_token")
    
    # Make request to logout endpoint
    response = client.get("/auth/logout", follow_redirects=False)
    
    # Assert it's a redirect to home
    assert response.status_code == 307
    assert response.headers["location"] == "/"
    
    # Verify the cookie deletion instruction is in the Set-Cookie header
    # When deleting a cookie, FastAPI sets it with max-age=0 to expire it
    set_cookie_header = response.headers.get("set-cookie", "")
    assert cookie_name in set_cookie_header
    assert "max-age=0" in set_cookie_header.lower() or "expires=" in set_cookie_header.lower()


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(monkeypatch):
    """Test that get_current_user returns steam_id from valid JWT cookie"""
    # Set up test JWT secret by patching the module variable
    test_jwt_secret = "test_secret_key_for_testing"
    
    # Import auth module to patch its jwt_secret_key
    from dota2_notify.web import auth
    monkeypatch.setattr(auth, "jwt_secret_key", test_jwt_secret)
    
    # Test Steam ID
    test_steam_id = "76561198012345678"
    
    # Create a valid JWT token
    token = jwt.encode({"sub": test_steam_id}, test_jwt_secret, algorithm="HS256")
    
    # Create a mock request with the cookie
    mock_request = MagicMock(spec=Request)
    mock_request.cookies.get.return_value = token
    
    # Call get_current_user
    result = await get_current_user(mock_request)
    
    # Verify it returns the correct steam_id
    assert result == test_steam_id
    
    # Verify the cookie was retrieved
    mock_request.cookies.get.assert_called_once_with(cookie_name)
