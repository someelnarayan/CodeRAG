import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:

    print("WARNING: REDIS_URL not set — Redis cache disabled")
    redis_client = None

else:

    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )