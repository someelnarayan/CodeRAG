import redis
import os
from dotenv import load_dotenv

# 🔴 LOAD .env FILE
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    # Do not crash at import time; allow running without Redis for local/dev setups.
    print("WARNING: REDIS_URL not set — Redis cache disabled")
    redis_client = None
else:
    redis_client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True
    )