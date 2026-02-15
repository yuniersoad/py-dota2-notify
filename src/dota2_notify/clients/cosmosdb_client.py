import asyncio
import logging
from typing import Optional, List
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from dota2_notify.models.user import User, Friend


class CosmosDbUserService:
    """Service for managing users in Cosmos DB."""
    STEAM_ID_OFFSET = 76561197960265728
    
    def __init__(self, cosmosdb_client: CosmosClient, database_name: str, container_name: str):
        """
        Initialize the Cosmos DB user service.
        
        Args:
            cosmosdb_client: Cosmos DB client instance
            database_name: Name of the database
            container_name: Name of the container
        """
        self._client = cosmosdb_client
        self._database_name = database_name
        self._container_name = container_name
        self._container = None
        self._logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def steam_id_to_account_id(self, steam_id: int) -> int:
        return steam_id - self.STEAM_ID_OFFSET
    
    def account_id_to_steam_id(self, account_id: int) -> int:
        return account_id + self.STEAM_ID_OFFSET
    
    async def connect(self):
        """Establish connection to Cosmos DB."""
        if self._client:
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
    
    async def create_user_async(self, account_id: int, name: str) -> User:
        user = User(
            id=str(account_id),
            user_id=account_id,
            name=name,
            telegram_chat_id="",
            following=True,
            type="user"
        )
        try:
            self._logger.info(f"Creating user with Account ID {account_id}")
            await self._container.create_item(user.to_dict())
            self._logger.info(f"Successfully created user {account_id}")
            return user
        except exceptions.CosmosResourceExistsError:
            self._logger.warning(f"User with Account ID {account_id} already exists")
            return await self.get_user_async(account_id)
        except Exception as ex:
            self._logger.error(f"Error creating user with Account ID {account_id}: {ex}")
            raise
    
    async def create_user_with_steam_id_async(self, steam_id: int, name: str) -> User:
        account_id = self.steam_id_to_account_id(steam_id)
        return await self.create_user_async(account_id, name)
    
    async def get_user_async(self, account_id: int) -> Optional[User]:
        try:
            self._logger.info(f"Getting user with ID {account_id}")
            
            response = await self._container.read_item(
                item=str(account_id),
                partition_key=account_id
            )
            
            self._logger.info(f"Successfully retrieved user {account_id}")
            return User.from_dict(response)
            
        except exceptions.CosmosResourceNotFoundError:
            self._logger.warning(f"User {account_id} not found")
            return None
        except Exception as ex:
            self._logger.error(f"Error getting user {account_id}: {ex}")
            raise
    
    async def get_user_with_steam_id_async(self, steam_id: int) -> Optional[User]:
        account_id = self.steam_id_to_account_id(steam_id)
        return await self.get_user_async(account_id)
    
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
    
    async def get_friends_async(self, account_id: int, following: Optional[bool] = None) -> List[Friend]:
        try:
            self._logger.info(f"Getting all friends for user {account_id}")
            
            if following is not None:
                query = "SELECT * FROM c WHERE c.type = 'friend' AND c.userId = @userId AND c.following = @following"
                parameters = [
                    {"name": "@userId", "value": account_id},
                    {"name": "@following", "value": following}
                ]
            else:
                query = "SELECT * FROM c WHERE c.type = 'friend' AND c.userId = @userId"
                parameters = [{"name": "@userId", "value": account_id}]
            
            friends = []
            
            async for item in self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=account_id
            ):
                friends.append(Friend.from_dict(item))
            
            self._logger.info(f"Retrieved {len(friends)} friends for user {account_id}")
            return friends
            
        except Exception as ex:
            self._logger.error(f"Error getting friends for user {account_id}: {ex}")
            raise
    
    async def get_friend_async(self, account_id: int, followed_player_id: int) -> Optional[Friend]:
        try:
            self._logger.info(f"Getting friend {followed_player_id} for user {account_id}")
            
            query = "SELECT * FROM c WHERE c.type = 'friend' AND c.userId = @userId AND c.id = @friendId"
            parameters = [
                {"name": "@userId", "value": account_id},
                {"name": "@friendId", "value": str(followed_player_id)}
            ]
            
            async for item in self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=account_id
            ):
                self._logger.info(f"Successfully retrieved friend {followed_player_id} for user {account_id}")
                return Friend.from_dict(item)
            
            self._logger.warning(f"Friend {followed_player_id} not found for user {account_id}")
            return None
            
        except Exception as ex:
            self._logger.error(f"Error getting friend {followed_player_id} for user {account_id}: {ex}")
            raise

    async def get_friend_by_steam_id_async(self, steam_id: int, friend_steam_id: int) -> Optional[Friend]:
        account_id = self.steam_id_to_account_id(steam_id)
        friend_account_id = self.steam_id_to_account_id(friend_steam_id)
        return await self.get_friend_async(account_id, friend_account_id)

    async def update_friend_async(self, friend: Friend):
        try:
            self._logger.info(f"Updating friend {friend.id} for user {friend.user_id}")
            await self._container.upsert_item(friend.to_dict())
            self._logger.info(f"Successfully updated friend {friend.id} for user {friend.user_id}")
        except Exception as ex:
            self._logger.error(f"Error updating friend {friend.id} for user {friend.user_id}: {ex}")
            raise
    
    async def update_last_match_id(self, account_id: int, followed_player_id: int, last_match_id: int):
        try:
            self._logger.info(f"Updating last match ID for user {account_id}, player {followed_player_id} to {last_match_id}")
            
            if account_id == followed_player_id:
                record = await self.get_user_async(account_id)
            else:
                record = await self.get_friend_async(account_id, followed_player_id)
            
            if record is None:
                self._logger.warning(f"User/Friend {account_id}, {followed_player_id} not found for update")
                return
            
            record.last_match_id = last_match_id
            await self._container.upsert_item(record.to_dict())
            self._logger.info(f"Successfully updated last match ID for user {account_id}, player {followed_player_id}")
            
        except Exception as ex:
            self._logger.error(f"Error updating last match ID for user {account_id}, player {followed_player_id}: {ex}")
            raise