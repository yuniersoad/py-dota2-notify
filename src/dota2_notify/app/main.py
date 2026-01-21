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

logging.basicConfig(level=logging.INFO)
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
    scheduler.add_job(check_new_matches, 'interval', seconds=10, args=[db_client, open_dota_client, telegram_client])
    scheduler.start()
    
    # pass control to the application
    yield

    # cleanup
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

def main():
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
