import redis
import json
from datetime import datetime, timezone

r = redis.Redis(host="localhost", port=6379, db=0)

def cache_gmail_token(user_id: str, credentials: dict, expiry):
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    ttl = int((expiry - datetime.now(timezone.utc)).total_seconds())

    redis_key = f"gmail:token:{user_id}"
    r.set(redis_key, json.dumps(credentials), ex=ttl)

def get_cached_gmail_token(user_id: str):
    redis_key = f"gmail:token:{user_id}"
    val = r.get(redis_key)
    return json.loads(val) if val else None