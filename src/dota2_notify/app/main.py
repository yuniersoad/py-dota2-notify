from dota2_notify.app.config import get_settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from dota2_notify.web import auth, health, friends, static, notifications
from azure.cosmos.aio import CosmosClient
import logging

import httpx
from dota2_notify.clients.cosmosdb_client import CosmosDbUserService 
from dota2_notify.clients.telegram_client import TelegramClient
from dota2_notify.clients.steam_client import SteamClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cosmosdb_client = CosmosClient(settings.cosmosdb_endpoint_uri, settings.cosmosdb_primary_key)
    db_client = CosmosDbUserService(
        cosmosdb_client=cosmosdb_client,
        database_name=settings.cosmosdb_database_name,
        user_container_name=settings.cosmosdb_container_name,
        telegram_verify_token_container_name=settings.cosmosdb_token_container_name
    )    
    await db_client.connect()
    app.state.user_service = db_client


     # Create httpx client with event hooks to redact sensitive data from logs
    async def log_request(request):
        url = str(request.url)
        url = url.replace(settings.telegram_bot_token, '[REDACTED]')
        url = url.replace(settings.steam_api_key, '[REDACTED]')
        logging.info(f"HTTP Request: {request.method} {url}")

    async def log_response(response):
        logging.info(f"HTTP Response: {response.status_code}")
    
    http_client = httpx.AsyncClient(
        event_hooks={'request': [log_request], 'response': [log_response]}
    )
    telegram_client = TelegramClient(token=settings.telegram_bot_token, client=http_client)
    steam_client = SteamClient(api_key=settings.steam_api_key,client=http_client)
    app.state.steam_client = steam_client

    # pass control to the application
    yield

    # cleanup
    await db_client.close()
    await http_client.aclose()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def flash_message_middleware(request: Request, call_next):
    flash_message = request.cookies.get("flash_message")
    if flash_message:
        request.state.flash_message = flash_message
    
    response = await call_next(request)
    
    if flash_message:
        response.delete_cookie("flash_message")
                
    return response

app.include_router(health.router)
app.include_router(friends.router)
app.include_router(auth.router)
app.include_router(notifications.router)
app.mount("/static", static.static_files, name="static")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

def main():
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
