import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import logging

import httpx
    

from dota2_notify.clients.cosmosdb_client import CosmosDbUserService 
from dota2_notify.clients.opendota_client import OpenDotaClient
from dota2_notify.clients.telegram_client import TelegramClient

logging.basicConfig(level=logging.INFO)
load_dotenv() 

async def check_new_matches(db_client: CosmosDbUserService, open_dota_client: OpenDotaClient, telegram_client: TelegramClient):
    logging.info("Checking for new matches...")
    users = await db_client.get_all_users_async()
    logging.info(f"Found {len(users)} users to check.")
    for user in users:
        logging.info("Checking user %s", user.id)
       
        for followed_player in user.following:
            logging.info("Checking for new matches for player %s (%s)", followed_player.user_id, followed_player.name)
            
            # Get recent matches for this player
            recent_matches = await open_dota_client.get_player_matches(followed_player.user_id, 1)
            
            if recent_matches[0].match_id == followed_player.last_match_id:
                logging.info("No new matches found for player %s (last match ID: %s)", followed_player.user_id, followed_player.last_match_id)
                continue
            
            newest_match = recent_matches[0]
            
            # Create notification message
            outcome = "✅ WON" if newest_match.player_won else "❌ LOST"
            match_duration_seconds = newest_match.duration
            hours = match_duration_seconds // 3600
            minutes = (match_duration_seconds % 3600) // 60
            seconds = match_duration_seconds % 60
            
            if hours >= 1:
                match_duration = f"{hours}h {minutes}m {seconds}s"
            else:
                match_duration = f"{minutes}m {seconds}s"
            
            dotabuff_link = f"https://www.dotabuff.com/matches/{newest_match.match_id}"
            message = (f"{followed_player.name} {outcome} a match as {newest_match.hero_name} "
                       f"with KDA {newest_match.kills}/{newest_match.deaths}/{newest_match.assists}. "
                       f"Match duration: {match_duration}. "
                       f"Match details: {dotabuff_link}")
            
            logging.info("Sending notification to user %s (ID: %s): %s", user.name, user.id, message)
            
            # Send notification
            await telegram_client.send_message(user.telegram_chat_id, message)
            
            # Update last seen match ID
            await db_client.update_last_match_id(user.user_id, followed_player.user_id, newest_match.match_id)
            
            logging.info("Updated last match ID for player %s to %s", followed_player.user_id, newest_match.match_id)

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
