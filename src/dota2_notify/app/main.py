import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
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
    telegram_client = TelegramClient(token=os.getenv("TELEGRAM__BOTTOKEN"), client=httpx.AsyncClient())
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

@app.get("/users")
async def get_users():
    # Reuse the persistent, non-blocking connection
    return await app.state.user_service.get_all_users_async()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Reuse the persistent, non-blocking connection
    user = await app.state.user_service.get_user_async(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def main():
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
