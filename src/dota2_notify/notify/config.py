from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cosmosdb_endpoint_uri: str = Field(..., alias="COSMOSDB__ENDPOINTURI")
    cosmosdb_primary_key: str = Field(..., alias="COSMOSDB__PRIMARYKEY")
    cosmosdb_database_name: str = Field(..., alias="COSMOSDB__DATABASENAME")
    cosmosdb_container_name: str = Field(..., alias="COSMOSDB__CONTAINERNAME")
    cosmosdb_token_container_name: str = Field(..., alias='COSMOSDB__TOKENCONTAINERNAME')
    cosmosdb_metadata_container_name: str = Field(..., alias="COSMOSDB__METADATACONTAINERNAME")

    steam_api_key: str = Field(..., alias='STEAM__APIKEY')

    telegram_bot_token: str = Field(..., alias='TELEGRAM__BOTTOKEN')

    redis_host: str = Field(..., alias="REDIS__HOST")
    redis_port: int = Field(..., alias="REDIS__PORT")

    poll_interval: float = Field(5.0, alias="POLL__INTERVAL")
    rate_limit_backoff_time: float = Field(60.0, alias="RATELIMIT__BACKOFFTIME")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="___",
        env_prefix="",
        extra="ignore",
    )


@lru_cache
def get_settings():
    return Settings()