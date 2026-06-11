import logging
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

# Use host 'redis' to connect to the Redis container in the same Docker network
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)


async def publish_slides_ready(class_code: str, output_dir: str) -> None:
    try:
        # Count the number of .webp files in the output directory
        total_slides = len([f for f in os.listdir(output_dir) if f.endswith(".webp")])

        # Publish JSON payload to redis
        payload = f'{{"class_code": "{class_code}", "total_slides": {total_slides}}}'
        await redis_client.publish("room_events", payload)
        logger.info(
            f"Published slides_ready for room {class_code}: {total_slides} slides."
        )
    except Exception as e:
        logger.error(f"Error publishing to Redis: {e}", exc_info=True)
