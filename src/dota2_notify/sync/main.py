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
keep_running = True

def handle_exit(sig, frame):
    global keep_running
    print("Shutdown signal received...")
    keep_running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def consume_change_feed(container, redis_client, poll_interval: float = 5.0) -> None:
    """Poll the Cosmos DB change feed indefinitely and print each changed document."""
    continuation = None
    iterations = 0
    initial_run_completed = False

    while keep_running:
        iterations += 1
        if iterations % 10 == 0:
            logger.info("Checking for Redis sentinel key...")
            sentinel_exists = await redis_client.exists(REDIS_SENTINEL_KEY)
            if not sentinel_exists:
                logger.warning("Redis sentinel key not found. Restarting from the beginning.")
                continuation = None
                initial_run_completed = False

        feed_kwargs = (
            {"continuation": continuation}
            if continuation
            else {"start_time": "Beginning"}
        )

        has_changes = False
        iterator = container.query_items_change_feed(**feed_kwargs)
        async for doc in iterator:
            has_changes = True
            print(json.dumps(doc, indent=2))
            if doc.get("following"):
                await redis_client.sadd(doc["id"], doc["userId"])
            else:
                await redis_client.srem(doc["id"], doc["userId"])
        
        if not continuation and not initial_run_completed:
            logger.info("Initial run completed. Setting Redis sentinel key.")
            await redis_client.set(REDIS_SENTINEL_KEY, "1")
            initial_run_completed = True

        continuation = container.client_connection.last_response_headers['etag']

        logger.debug("Checked for changes. Continuation token: %s", continuation)

        if not has_changes:
            logger.debug("No changes. Waiting %ss before next poll.", poll_interval)
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
        container = client.get_database_client(settings.cosmosdb_database_name).get_container_client(
            settings.cosmosdb_container_name
        )
        logger.info(
            "Listening to change feed on %s/%s",
            settings.cosmosdb_database_name,
            settings.cosmosdb_container_name,
        )
        await consume_change_feed(container, redis_client)

    logger.info("Shutting down Redis client...")
    await redis_client.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    run()