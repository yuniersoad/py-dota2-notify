import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dota2_notify.web import users, auth, health, friends, static
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import logging

import httpx
    
from dota2_notify.app.match_checker import check_new_matches
from dota2_notify.clients.cosmosdb_client import CosmosDbUserService 
from dota2_notify.clients.opendota_client import OpenDotaClient
from dota2_notify.clients.telegram_client import TelegramClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_client = CosmosDbUserService(
        connection_endpoint=os.getenv("COSMOSDB__ENDPOINTURI"),
        key=os.getenv("COSMOSDB__PRIMARYKEY"),
        database_name=os.getenv("COSMOSDB__DATABASENAME"),
        container_name=os.getenv("COSMOSDB__CONTAINERNAME")
    )    
    await db_client.connect()
    app.state.user_service = db_client

    open_dota_client = OpenDotaClient(client=httpx.AsyncClient())

    # Create httpx client with event hooks to redact sensitive data from logs
    async def log_request(request):
        logging.info(f"HTTP Request: {request.method} {str(request.url).replace(os.getenv('TELEGRAM__BOTTOKEN', ''), '[REDACTED]')}")

    async def log_response(response):
        logging.info(f"HTTP Response: {response.status_code}")

    telegram_http_client = httpx.AsyncClient(
        event_hooks={'request': [log_request], 'response': [log_response]}
    )
    telegram_client = TelegramClient(token=os.getenv("TELEGRAM__BOTTOKEN"), client=telegram_http_client)
    scheduler = AsyncIOScheduler()

    check_enabled = os.getenv("MATCHCHECK__ENABLED", "true").lower() in ("true", "1", "yes")
    if check_enabled:
        interval_minutes = int(os.getenv("MATCHCHECK__INTERVALMINUTES", "5"))
        logging.info(f"Match checking is enabled. Scheduling periodic match checks. Every {interval_minutes} minutes.")
        scheduler.add_job(check_new_matches, 'interval', minutes=interval_minutes, args=[db_client, open_dota_client, telegram_client])
        scheduler.start()
    else:
        logging.info("Match checking is disabled. No periodic match checks will be scheduled.")
    
    # pass control to the application
    yield

    # cleanup
    if check_enabled:
        scheduler.shutdown()
    await db_client.close()
    await open_dota_client.client.aclose()
    await telegram_client.client.aclose()

app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(health.router)
app.include_router(friends.router)
app.include_router(auth.router)
app.mount("/static", static.static_files, name="static")

def main():
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
