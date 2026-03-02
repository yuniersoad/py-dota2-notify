import asyncio
import json
import logging

from azure.cosmos.aio import CosmosClient
from dota2_notify.sync.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)


async def consume_change_feed(container, poll_interval: float = 5.0) -> None:
    """Poll the Cosmos DB change feed indefinitely and print each changed document."""
    continuation = None

    while True:
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
        continuation = container.client_connection.last_response_headers['etag']

        logger.debug("Checked for changes. Continuation token: %s", continuation)

        if not has_changes:
            logger.debug("No changes. Waiting %ss before next poll.", poll_interval)
            await asyncio.sleep(poll_interval)


async def main() -> None:
    settings = get_settings()

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
        await consume_change_feed(container)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()