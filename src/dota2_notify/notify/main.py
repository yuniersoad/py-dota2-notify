import asyncio
import logging
import signal
import time
import httpx
import redis.asyncio as redis

from azure.cosmos.aio import CosmosClient
from dota2_notify.clients.cosmosdb_client import CosmosDbUserService
from dota2_notify.clients.steam_client import SteamClient
from dota2_notify.clients.telegram_client import TelegramClient
from dota2_notify.notify.config import get_settings
from dota2_notify.models.match import Match

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

keep_running = True


def handle_exit(sig, frame):
    global keep_running
    print("Shutdown signal received...")
    keep_running = False


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def send_notification(user_id: int, account_id: int, match: Match, db_client: CosmosDbUserService, telegram_client: TelegramClient):
    """Send a notification to a user about a match."""
    notified_user = await db_client.get_user_async(user_id)
    if not notified_user or not notified_user.telegram_chat_id:
        logger.warning(f"User {user_id} not found or has no telegram chat id.")
        return

    player_in_match = next((p for p in match.players if p.account_id == account_id), None)
    if not player_in_match:
        logger.warning(f"Player {account_id} not found in match {match.match_id}")
        return

    if user_id == account_id:
        followed_player_name = notified_user.name
    else:
        friend = await db_client.get_friend_async(user_id, account_id)
        if not friend:
            logger.warning(f"Friendship between user {user_id} and player {account_id} not found.")
            return
        followed_player_name = friend.name

    hero_name = player_in_match.hero_name
    player_won = (player_in_match.player_slot < 128 and match.radiant_win) or \
                 (player_in_match.player_slot >= 128 and not match.radiant_win)

    outcome = "✅ Won" if player_won else "❌ Lost"
    match_duration_seconds = match.duration
    hours = match_duration_seconds // 3600
    minutes = (match_duration_seconds % 3600) // 60
    seconds = match_duration_seconds % 60

    if hours >= 1:
        match_duration = f"{hours}h {minutes}m {seconds}s"
    else:
        match_duration = f"{minutes}m {seconds}s"

    dotabuff_link = f"https://www.dotabuff.com/matches/{match.match_id}"
    message = (f"{followed_player_name} {outcome} a match as {hero_name} "
               f"with KDA {player_in_match.kills}/{player_in_match.deaths}/{player_in_match.assists}. "
               f"Match duration: {match_duration}. "
               f"Match details: {dotabuff_link}")

    logging.info("Sending notification to user %s (ID: %s): %s", notified_user.name, notified_user.id, message)

    await telegram_client.send_message(notified_user.telegram_chat_id, message)
    #await db_client.update_last_match_id(user_id, account_id, match.match_id)


async def process_match(match: Match, redis_client: redis.Redis, db_client: CosmosDbUserService, telegram_client: TelegramClient):
    """Process a single match to find and notify users."""
    public_players = [
        p.account_id
        for p in match.players
        if p.account_id not in [0, 4294967295]
    ]

    if not public_players:
        return

    pipe = redis_client.pipeline()
    for account_id in public_players:
        pipe.smembers(str(account_id))
    
    try:
        results = await pipe.execute()
        
        for i, account_id in enumerate(public_players):
            user_ids_to_notify = results[i]
            if user_ids_to_notify:
                for user_id_bytes in user_ids_to_notify:
                    user_id = int(user_id_bytes.decode('utf-8'))
                    logger.info(f"User {user_id} should be notified about player {account_id} in match {match.match_id}")
                    await send_notification(user_id, account_id, match, db_client, telegram_client)
    except redis.RedisError as e:
        logger.error(f"Redis error while processing match {match.match_id}: {e}")


MATCH_SEQ_NUM_DOC_ID = "dota2_notify_match_seq_num"


async def get_match_sequence_num(metadata_container):
    try:
        metadata_doc = await metadata_container.read_item(
            item=MATCH_SEQ_NUM_DOC_ID, partition_key=MATCH_SEQ_NUM_DOC_ID
        )
        return metadata_doc.get("value")
    except Exception:
        return None


async def save_match_sequence_num(metadata_container, seq_num):
    metadata_doc = {
        "id": MATCH_SEQ_NUM_DOC_ID,
        "value": seq_num,
    }
    await metadata_container.upsert_item(body=metadata_doc)


async def consume_match_feed(steam_client: SteamClient, redis_client: redis.Redis, db_client: CosmosDbUserService, telegram_client: TelegramClient, metadata_container, poll_interval: float = 5.0):
    """Poll the Steam API for new matches indefinitely."""
    start_at_match_seq_num = await get_match_sequence_num(metadata_container)
    batch_size = 100
    iterations = 0

    if start_at_match_seq_num is None:
        return

    while keep_running:
        try:
            iterations += 1
            logger.info(f"Fetching matches starting from sequence number {start_at_match_seq_num}")
            match_history = await steam_client.get_match_history_by_sequence_num(
                start_at_match_seq_num=start_at_match_seq_num,
                matches_requested=batch_size
            )

            matches = match_history.result.matches
            if matches:
                first_seq_num, first_match_id = matches[0].match_seq_num, matches[0].match_id
                last_seq_num, last_match_id = matches[-1].match_seq_num, matches[-1].match_id

                for match in matches:
                    await process_match(match, redis_client, db_client, telegram_client)

                last_match = matches[-1]
                last_match_end_time = last_match.start_time + last_match.duration
                current_time = int(time.time())
                lag_seconds = current_time - last_match_end_time
                lag_minutes, lag_secs = divmod(lag_seconds, 60)

                logger.info(f"Processed batch of {len(matches)} matches. Sequence: {first_seq_num} ({first_match_id}) to {last_seq_num} ({last_match_id}). Lag: {lag_minutes}m {lag_secs}s.")

                start_at_match_seq_num = last_seq_num + 1
                if iterations % 5 == 0:
                    logger.info(f"Saving next sequence number to DB: {start_at_match_seq_num}")
                    await save_match_sequence_num(metadata_container, start_at_match_seq_num)
            else:
                logger.info("No new matches found.")
                await asyncio.sleep(2*poll_interval)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 or e.response.status_code == 503:
                logger.warning("Rate limit hit. Waiting for 60 seconds.")
                await asyncio.sleep(60)
                continue
            else:
                logger.error(f"HTTP error while fetching matches: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

        sleep_time = poll_interval
        # we are up to date, can wait longer before next poll
        if len(matches) < (batch_size * 0.9): 
            sleep_time = 2*poll_interval
        # we are not likely up to date, but valve removes some "private" matches, so we got less matches than requested
        # adding some time for randomization
        elif len(matches) < batch_size and len(matches) >= (batch_size * 0.9): 
            sleep_time = poll_interval + 1.0
        
        logger.info("Waiting %ss before next poll.", sleep_time) 
        await asyncio.sleep(sleep_time)


async def main() -> None:
    settings = get_settings()

    logger.info("Connecting to Redis: %s:%s", settings.redis_host, settings.redis_port)
    redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0)

    async with httpx.AsyncClient() as http_client, CosmosClient(
        url=settings.cosmosdb_endpoint_uri,
        credential=settings.cosmosdb_primary_key,
    ) as cosmos_client:
        steam_client = SteamClient(api_key=settings.steam_api_key, client=http_client)
        telegram_client = TelegramClient(token=settings.telegram_bot_token, client=http_client)
        db_client = CosmosDbUserService(
            cosmosdb_client=cosmos_client,
            database_name=settings.cosmosdb_database_name,
            user_container_name=settings.cosmosdb_container_name,
            telegram_verify_token_container_name=settings.cosmosdb_token_container_name
        )
        await db_client.connect()

        database = cosmos_client.get_database_client(settings.cosmosdb_database_name)
        metadata_container = database.get_container_client(settings.cosmosdb_metadata_container_name)
        
        logger.info("Starting match feed consumer...")
        await consume_match_feed(steam_client, redis_client, db_client, telegram_client, metadata_container)

    logger.info("Shutting down Redis client...")
    await redis_client.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    run()
