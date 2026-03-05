import os
from rq import Queue
from redis import Redis

def get_queue():
    sync = os.getenv("RQ_SYNC", "1") == "1"
    if sync:
        return Queue("default", is_async=False)
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Queue("default", connection=Redis.from_url(url))