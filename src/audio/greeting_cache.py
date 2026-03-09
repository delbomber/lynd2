"""Simple Redis-based cache for pre-generated greeting audio."""
import logging
import ssl
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

GREETING_TTL = 300  # 5 minutes


def _get_redis(redis_url: str):
    import redis

    parsed = urlparse(redis_url)
    use_ssl = redis_url.startswith("rediss://")
    return redis.Redis(
        host=parsed.hostname,
        port=parsed.port or (6380 if use_ssl else 6379),
        password=parsed.password,
        ssl=use_ssl,
        ssl_cert_reqs=None if use_ssl else ssl.CERT_REQUIRED,
    )


def cache_greeting_audio(job_id: int, audio_bytes: bytes, redis_url: str) -> None:
    r = _get_redis(redis_url)
    r.setex(f"greeting:{job_id}", GREETING_TTL, audio_bytes)


def get_greeting_audio(job_id: int, redis_url: str) -> bytes | None:
    r = _get_redis(redis_url)
    return r.get(f"greeting:{job_id}")
