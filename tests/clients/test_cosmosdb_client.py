import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dota2_notify.clients.cosmosdb_client import CosmosDbUserService
from dota2_notify.models.user import User, Friend

@pytest.mark.asyncio
async def test_get_user_async():
    mock_user_data = {
        "id": "user-123",
        "userId": 123,
        "name": "TestUser",
        "telegramChatId": "chat-456",
        "following": [],
        "type": "user"
    }
    
    mock_container = AsyncMock()
    mock_container.read_item.return_value = mock_user_data
    
    with patch('dota2_notify.clients.cosmosdb_client.CosmosClient') as MockCosmosClient:
        mock_client_instance = MockCosmosClient.return_value
        mock_database = mock_client_instance.get_database_client.return_value
        mock_database.get_container_client.return_value = mock_container
        mock_client_instance.close = AsyncMock()
        
        async with CosmosDbUserService(
            connection_endpoint="https://fake-endpoint.documents.azure.com:443/",
            key="fake-key",
            database_name="test-db",
            container_name="test-container"
        ) as service:
            user = await service.get_user_async(account_id=123)
            
            assert user is not None
            assert user.id == "user-123"
            assert user.user_id == 123
            assert user.name == "TestUser"
            assert user.telegram_chat_id == "chat-456"
            assert user.following == []
            assert user.type == "user"
            
            mock_container.read_item.assert_awaited_once_with(item="123", partition_key=123)

@pytest.mark.asyncio
async def test_get_all_users_async():
    mock_user_data_list = [
        {
            "id": "user-123",
            "userId": 123,
            "name": "TestUser1",
            "telegramChatId": "chat-456",
            "following": [],
            "type": "user"
        },
        {
            "id": "user-456",
            "userId": 456,
            "name": "TestUser2",
            "telegramChatId": "chat-789",
            "following": [],
            "type": "user"
        }
    ]
    
    async def mock_query_iterator(*args, **kwargs):
        for item in mock_user_data_list:
            yield item
    
    mock_container = MagicMock()
    mock_container.query_items.side_effect = mock_query_iterator
    
    with patch('dota2_notify.clients.cosmosdb_client.CosmosClient') as MockCosmosClient:
        mock_client_instance = MockCosmosClient.return_value
        mock_database = mock_client_instance.get_database_client.return_value
        mock_database.get_container_client.return_value = mock_container
        mock_client_instance.close = AsyncMock()
        
        async with CosmosDbUserService(
            connection_endpoint="https://fake-endpoint.documents.azure.com:443/",
            key="fake-key",
            database_name="test-db",
            container_name="test-container"
        ) as service:
            users = await service.get_all_users_async()
            
            
            assert len(users) == 2
            assert users[0].user_id == 123
            assert users[1].user_id == 456
            
            mock_container.query_items.assert_called_once()

@pytest.mark.asyncio
async def test_get_friends_async():
    mock_friends_data_list = [
        {
            "id": "1111263425",
            "userId": 123,
            "name": "Friend One",
            "lastMatchId": 8683839389,
            "following": True,
            "type": "friend"
        },
        {
            "id": "2222263425",
            "userId": 123,
            "name": "Friend Two",
            "lastMatchId": 8683839390,
            "following": False,
            "type": "friend"
        }
    ]
    
    async def mock_query_iterator(*args, **kwargs):
        for item in mock_friends_data_list:
            yield item
    
    mock_container = MagicMock()
    mock_container.query_items.side_effect = mock_query_iterator
    
    with patch('dota2_notify.clients.cosmosdb_client.CosmosClient') as MockCosmosClient:
        mock_client_instance = MockCosmosClient.return_value
        mock_database = mock_client_instance.get_database_client.return_value
        mock_database.get_container_client.return_value = mock_container
        mock_client_instance.close = AsyncMock()
        
        async with CosmosDbUserService(
            connection_endpoint="https://fake-endpoint.documents.azure.com:443/",
            key="fake-key",
            database_name="test-db",
            container_name="test-container"
        ) as service:
            friends = await service.get_friends_async(account_id=123)
            
            assert len(friends) == 2
            assert friends[0].id == "1111263425"
            assert friends[0].user_id == 123
            assert friends[0].name == "Friend One"
            assert friends[0].last_match_id == 8683839389
            assert friends[0].following is True
            assert friends[0].type == "friend"
            
            assert friends[1].id == "2222263425"
            assert friends[1].user_id == 123
            assert friends[1].name == "Friend Two"
            assert friends[1].last_match_id == 8683839390
            assert friends[1].following is False
            assert friends[1].type == "friend"
            
            mock_container.query_items.assert_called_once()

@pytest.mark.asyncio
async def test_get_friend_async():
    mock_friend_data = {
        "id": "1111263425",
        "userId": 123,
        "name": "Friend One",
        "lastMatchId": 8683839389,
        "following": True,
        "type": "friend"
    }
    
    async def mock_query_iterator(*args, **kwargs):
        yield mock_friend_data
    
    mock_container = MagicMock()
    mock_container.query_items.side_effect = mock_query_iterator
    
    with patch('dota2_notify.clients.cosmosdb_client.CosmosClient') as MockCosmosClient:
        mock_client_instance = MockCosmosClient.return_value
        mock_database = mock_client_instance.get_database_client.return_value
        mock_database.get_container_client.return_value = mock_container
        mock_client_instance.close = AsyncMock()
        
        async with CosmosDbUserService(
            connection_endpoint="https://fake-endpoint.documents.azure.com:443/",
            key="fake-key",
            database_name="test-db",
            container_name="test-container"
        ) as service:
            friend = await service.get_friend_async(account_id=123, followed_player_id=1111263425)
            
            assert friend is not None
            assert friend.id == "1111263425"
            assert friend.user_id == 123
            assert friend.name == "Friend One"
            assert friend.last_match_id == 8683839389
            assert friend.following is True
            assert friend.type == "friend"
            
            mock_container.query_items.assert_called_once()

@pytest.mark.asyncio
async def test_update_last_match_id_for_friend():
    mock_friend_data = {
        "id": "1111263425",
        "userId": 123,
        "name": "Friend One",
        "lastMatchId": 8683839389,
        "following": True,
        "type": "friend"
    }
    
    async def mock_query_iterator(*args, **kwargs):
        yield mock_friend_data
    
    mock_container = MagicMock()
    mock_container.query_items.side_effect = mock_query_iterator
    mock_container.upsert_item = AsyncMock()
    
    with patch('dota2_notify.clients.cosmosdb_client.CosmosClient') as MockCosmosClient:
        mock_client_instance = MockCosmosClient.return_value
        mock_database = mock_client_instance.get_database_client.return_value
        mock_database.get_container_client.return_value = mock_container
        mock_client_instance.close = AsyncMock()
        
        async with CosmosDbUserService(
            connection_endpoint="https://fake-endpoint.documents.azure.com:443/",
            key="fake-key",
            database_name="test-db",
            container_name="test-container"
        ) as service:
            await service.update_last_match_id(
                account_id=123,
                followed_player_id=1111263425,
                last_match_id=9999999999
            )
            
            mock_container.upsert_item.assert_awaited_once()
            upserted_data = mock_container.upsert_item.call_args[0][0]
            assert upserted_data["lastMatchId"] == 9999999999
            assert upserted_data["id"] == "1111263425"
            assert upserted_data["userId"] == 123
