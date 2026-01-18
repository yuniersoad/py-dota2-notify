import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import logging
    

from dota2_notify.clients.cosmosdb_client import CosmosDbUserService 

logging.basicConfig(level=logging.INFO)
load_dotenv() 

def check_new_matches(service: CosmosDbUserService):
    logging.info("Checking for new matches...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    service = CosmosDbUserService(
        connection_endpoint=os.getenv("COSMOSDB__ENDPOINTURI"),
        key=os.getenv("COSMOSDB__PRIMARYKEY"),
        database_name=os.getenv("COSMOSDB__DATABASENAME"),
        container_name=os.getenv("COSMOSDB__CONTAINERNAME")
    )
    await service.connect()
    app.state.user_service = service
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_matches, 'interval', seconds=10, args=[service])
    scheduler.start()
    
    # pass control to the application
    yield

    # cleanup
    scheduler.shutdown()
    await service.close()
   
    
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
