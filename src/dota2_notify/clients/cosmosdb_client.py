import asyncio
from azure.cosmos.aio import CosmosClient

import logging
from typing import Optional, List
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from dota2_notify.models.user import User


class CosmosDbUserService:
    """Service for managing users in Cosmos DB."""
    
    def __init__(self, connection_endpoint: str, key: str, database_name: str, container_name: str):
        """
        Initialize the Cosmos DB user service.
        
        Args:
            connection_endpoint: Cosmos DB connection endpoint
            key: Cosmos DB key
            database_name: Name of the database
            container_name: Name of the container
        """
        self._connection_endpoint = connection_endpoint
        self._key = key
        self._database_name = database_name
        self._container_name = container_name
        self._client: Optional[CosmosClient] = None
        self._container = None
        self._logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Establish connection to Cosmos DB."""
        if self._client is None:
            self._client = CosmosClient(self._connection_endpoint, credential=self._key)
            database = self._client.get_database_client(self._database_name)
            self._container = database.get_container_client(self._container_name)
            self._logger.info(f"Connected to Cosmos DB: {self._database_name}/{self._container_name}")
    
    async def close(self):
        """Close the Cosmos DB connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._container = None
            self._logger.info("Closed Cosmos DB connection")
    
    async def get_user_async(self, user_id: int) -> Optional[User]:
        try:
            self._logger.info(f"Getting user with ID {user_id}")
            
            response = await self._container.read_item(
                item=str(user_id),
                partition_key=user_id
            )
            
            self._logger.info(f"Successfully retrieved user {user_id}")
            return User.from_dict(response)
            
        except exceptions.CosmosResourceNotFoundError:
            self._logger.warning(f"User {user_id} not found")
            return None
        except Exception as ex:
            self._logger.error(f"Error getting user {user_id}: {ex}")
            raise
    
    async def get_all_users_async(self) -> List[User]:
        try:
            self._logger.info("Getting all users")
            
            query = "SELECT * FROM c WHERE c.type = 'user'"
            users = []
            
            async for item in self._container.query_items(
                query=query
            ):
                users.append(User.from_dict(item))
            
            self._logger.info(f"Retrieved {len(users)} users")
            return users
            
        except Exception as ex:
            self._logger.error(f"Error getting all users: {ex}")
            raise
    
    async def update_last_match_id(self, user_id: int, followed_player_id: int, last_match_id: int):
        try:
            self._logger.info(f"Updating last match ID for user {user_id}, player {followed_player_id} to {last_match_id}")
            
            user = await self.get_user_async(user_id)
            if user is None:
                self._logger.warning(f"User {user_id} not found for update")
                return
            
            for player in user.following:
                if player.user_id == followed_player_id:
                    player.last_match_id = last_match_id
                    break
            
            await self._container.upsert_item(user.to_dict())
            self._logger.info(f"Successfully updated last match ID for user {user_id}, player {followed_player_id}")
            
        except Exception as ex:
            self._logger.error(f"Error updating last match ID for user {user_id}, player {followed_player_id}: {ex}")
            raise