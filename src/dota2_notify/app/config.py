from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import cache

class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., alias='TELEGRAM__BOTTOKEN')
    cosmosdb_endpoint_uri: str = Field(..., alias='COSMOSDB__ENDPOINTURI')
    cosmosdb_primary_key: str = Field(..., alias='COSMOSDB__PRIMARYKEY')
    cosmosdb_database_name: str = Field(..., alias='COSMOSDB__DATABASENAME')
    cosmosdb_container_name: str = Field(..., alias='COSMOSDB__CONTAINERNAME')
    cosmosdb_token_container_name: str = Field(..., alias='COSMOSDB__TOKENCONTAINERNAME')
    matchcheck_interval_minutes: int = Field(..., alias='MATCHCHECK__INTERVALMINUTES')
    matchcheck_enabled: bool = Field(..., alias='MATCHCHECK__ENABLED')
    steam_api_key: str = Field(..., alias='STEAM__APIKEY')
    jwt_cookies_secret: str = Field(..., alias='JWT__COOKIES__SECRET')
    openapi_path: str = Field("/openapi.json", alias='OPENAPI__PATH')
    redis_host: str = Field(..., alias="REDIS__HOST")
    redis_port: int = Field(..., alias="REDIS__PORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter='___',
        env_prefix='',
        extra="ignore",
    )

@cache
def get_settings():
    return Settings()