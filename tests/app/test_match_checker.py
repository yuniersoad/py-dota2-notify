import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dota2_notify.app.match_checker import check_new_matches


@pytest.fixture
def mock_db_client():
    return AsyncMock()


@pytest.fixture
def mock_opendota_client():
    return AsyncMock()


@pytest.fixture
def mock_telegram_client():
    return AsyncMock()


@pytest.mark.asyncio
async def test_check_new_matches_no_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client):
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "user123"
    mock_user.name = "Test User"
    mock_user.user_id = "user123"
    mock_user.telegram_chat_id = "chat123"
    
    mock_followed_player = MagicMock()
    mock_followed_player.user_id = "player456"
    mock_followed_player.name = "ProPlayer"
    mock_followed_player.last_match_id = 7890
    
    mock_user.following = [mock_followed_player]
    
    mock_match = MagicMock()
    mock_match.match_id = 7890
    
    mock_db_client.get_all_users_async.return_value = [mock_user]
    mock_opendota_client.get_player_matches.return_value = [mock_match]
    
    # Act
    await check_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client)
    
    # Assert
    mock_telegram_client.send_message.assert_not_called()
    mock_db_client.update_last_match_id.assert_not_called()


@pytest.mark.asyncio
async def test_check_new_matches_new_match_found_won(mock_db_client, mock_opendota_client, mock_telegram_client):
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "user123"
    mock_user.name = "Test User"
    mock_user.user_id = "user123"
    mock_user.telegram_chat_id = "chat123"
    
    mock_followed_player = MagicMock()
    mock_followed_player.user_id = "player456"
    mock_followed_player.name = "ProPlayer"
    mock_followed_player.last_match_id = 7890
    
    mock_user.following = [mock_followed_player]
    
    mock_match = MagicMock()
    mock_match.match_id = 7891
    mock_match.player_won = True
    mock_match.hero_name = "Anti-Mage"
    mock_match.kills = 10
    mock_match.deaths = 2
    mock_match.assists = 15
    mock_match.duration = 2400  # 40 minutes
    
    mock_db_client.get_all_users_async.return_value = [mock_user]
    mock_opendota_client.get_player_matches.return_value = [mock_match]
    
    # Act
    await check_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client)
    
    # Assert
    expected_message = (
        "ProPlayer ✅ Won a match as Anti-Mage with KDA 10/2/15. "
        "Match duration: 40m 0s. "
        "Match details: https://www.dotabuff.com/matches/7891"
    )
    mock_telegram_client.send_message.assert_called_once_with("chat123", expected_message)
    mock_db_client.update_last_match_id.assert_called_once_with("user123", "player456", 7891)


@pytest.mark.asyncio
async def test_check_new_matches_new_match_found_lost(mock_db_client, mock_opendota_client, mock_telegram_client):
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "user123"
    mock_user.name = "Test User"
    mock_user.user_id = "user123"
    mock_user.telegram_chat_id = "chat123"
    
    mock_followed_player = MagicMock()
    mock_followed_player.user_id = "player456"
    mock_followed_player.name = "ProPlayer"
    mock_followed_player.last_match_id = 7890
    
    mock_user.following = [mock_followed_player]
    
    mock_match = MagicMock()
    mock_match.match_id = 7891
    mock_match.player_won = False
    mock_match.hero_name = "Invoker"
    mock_match.kills = 5
    mock_match.deaths = 8
    mock_match.assists = 12
    mock_match.duration = 1845  # 30m 45s
    
    mock_db_client.get_all_users_async.return_value = [mock_user]
    mock_opendota_client.get_player_matches.return_value = [mock_match]
    
    # Act
    await check_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client)
    
    # Assert
    expected_message = (
        "ProPlayer ❌ Lost a match as Invoker with KDA 5/8/12. "
        "Match duration: 30m 45s. "
        "Match details: https://www.dotabuff.com/matches/7891"
    )
    mock_telegram_client.send_message.assert_called_once_with("chat123", expected_message)
    mock_db_client.update_last_match_id.assert_called_once_with("user123", "player456", 7891)


@pytest.mark.asyncio
async def test_check_new_matches_long_duration_format(mock_db_client, mock_opendota_client, mock_telegram_client):
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "user123"
    mock_user.name = "Test User"
    mock_user.user_id = "user123"
    mock_user.telegram_chat_id = "chat123"
    
    mock_followed_player = MagicMock()
    mock_followed_player.user_id = "player456"
    mock_followed_player.name = "ProPlayer"
    mock_followed_player.last_match_id = 7890
    
    mock_user.following = [mock_followed_player]
    
    mock_match = MagicMock()
    mock_match.match_id = 7891
    mock_match.player_won = True
    mock_match.hero_name = "Techies"
    mock_match.kills = 3
    mock_match.deaths = 1
    mock_match.assists = 20
    mock_match.duration = 5430  # 1h 30m 30s
    
    mock_db_client.get_all_users_async.return_value = [mock_user]
    mock_opendota_client.get_player_matches.return_value = [mock_match]
    
    # Act
    await check_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client)
    
    # Assert
    expected_message = (
        "ProPlayer ✅ Won a match as Techies with KDA 3/1/20. "
        "Match duration: 1h 30m 30s. "
        "Match details: https://www.dotabuff.com/matches/7891"
    )
    mock_telegram_client.send_message.assert_called_once_with("chat123", expected_message)


@pytest.mark.asyncio
async def test_check_new_matches_no_users(mock_db_client, mock_opendota_client, mock_telegram_client):
    # Arrange
    mock_db_client.get_all_users_async.return_value = []
    
    # Act
    await check_new_matches(mock_db_client, mock_opendota_client, mock_telegram_client)
    
    # Assert
    mock_opendota_client.get_player_matches.assert_not_called()
    mock_telegram_client.send_message.assert_not_called()