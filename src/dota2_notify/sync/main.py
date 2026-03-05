import asyncio
import json
import logging
import signal
import redis.asyncio as redis

from azure.cosmos.aio import CosmosClient
from dota2_notify.sync.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)

REDIS_SENTINEL_KEY = "dota2_notify_sync_sentinel"
FEED_CONTINUATION_TOKEN_DOC_ID = "feed_continuation_token"
keep_running = True


def handle_exit(sig, frame):
    global keep_running
    print("Shutdown signal received...")
    keep_running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def get_continuation_token(metadata_container):
    try:
        metadata_doc = await metadata_container.read_item(
            item=FEED_CONTINUATION_TOKEN_DOC_ID, partition_key=FEED_CONTINUATION_TOKEN_DOC_ID
        )
        return metadata_doc.get("continuation_token")
    except Exception:
        return None


async def save_continuation_token(metadata_container, token):
    metadata_doc = {
        "id": FEED_CONTINUATION_TOKEN_DOC_ID,
        "continuation_token": token,
    }
    await metadata_container.upsert_item(body=metadata_doc)


async def delete_continuation_token(metadata_container):
    try:
        await metadata_container.delete_item(
            item=FEED_CONTINUATION_TOKEN_DOC_ID, partition_key=FEED_CONTINUATION_TOKEN_DOC_ID
        )
    except Exception:
        pass


async def consume_change_feed(
    container, metadata_container, redis_client, poll_interval: float = 5.0
) -> None:
    """Poll the Cosmos DB change feed indefinitely and print each changed document."""
    continuation = await get_continuation_token(metadata_container)
    iterations = 0
    initial_run_completed = False

    while keep_running:
        iterations += 1
        if iterations % 10 == 0:
            try:
                logger.info("Checking for Redis sentinel key...")
                sentinel_exists = await redis_client.exists(REDIS_SENTINEL_KEY)
                if not sentinel_exists:
                    logger.warning("Redis sentinel key not found. Restarting from the beginning.")
                    continuation = None
                    initial_run_completed = False
                    await delete_continuation_token(metadata_container)
            except redis.RedisError as e:
                logger.error(f"Redis error when checking sentinel key: {e}")

        feed_kwargs = (
            {"continuation": continuation} if continuation else {"start_time": "Beginning"}
        )

        try:
            iterator = container.query_items_change_feed(**feed_kwargs)
            async for doc in iterator:
                print(json.dumps(doc, indent=2))
                if doc.get("following"):
                    await redis_client.sadd(doc["id"], doc["userId"])
                else:
                    await redis_client.srem(doc["id"], doc["userId"])
        except redis.RedisError as e:
            logger.error(f"Redis error during change feed processing: {e}. Retrying batch.")
            await asyncio.sleep(poll_interval)
            continue

        if not continuation and not initial_run_completed:
            try:
                logger.info("Initial run completed. Setting Redis sentinel key.")
                await redis_client.set(REDIS_SENTINEL_KEY, "1")
                initial_run_completed = True
            except redis.RedisError as e:
                logger.error(f"Redis error when setting sentinel key: {e}")

        new_continuation = container.client_connection.last_response_headers.get("etag")
        if new_continuation and new_continuation != continuation:
            continuation = new_continuation
            await save_continuation_token(metadata_container, continuation)

        logger.debug("Checked for changes. Continuation token: %s", continuation)

        logger.debug("Waiting %ss before next poll.", poll_interval)
        await asyncio.sleep(poll_interval)


async def main() -> None:
    settings = get_settings()

    logger.info("Connecting to Redis: %s:%s", settings.redis_host, settings.redis_port)
    redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0)

    logger.info("Connecting to Cosmos DB: %s", settings.cosmosdb_endpoint_uri)
    async with CosmosClient(
        url=settings.cosmosdb_endpoint_uri,
        credential=settings.cosmosdb_primary_key,
    ) as client:
        database = client.get_database_client(settings.cosmosdb_database_name)
        container = database.get_container_client(settings.cosmosdb_container_name)
        metadata_container = database.get_container_client(settings.cosmosdb_metadata_container_name)
        logger.info(
            "Listening to change feed on %s/%s",
            settings.cosmosdb_database_name,
            settings.cosmosdb_container_name,
        )
        await consume_change_feed(container, metadata_container, redis_client)

    logger.info("Shutting down Redis client...")
    await redis_client.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    run()