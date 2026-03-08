import os
import ssl
from celery import Celery

celery_app = Celery("lynd")


def _apply_redis_config(redis_url: str):
    """Configure Celery broker and backend, handling TLS for Upstash."""
    celery_app.conf.broker_url = redis_url
    celery_app.conf.result_backend = redis_url
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"

    if redis_url.startswith("rediss://"):
        celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
        celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}


# Auto-configure when running as standalone worker
if os.environ.get("REDIS_URL"):
    _apply_redis_config(os.environ["REDIS_URL"])

# Import tasks so they are registered with the app
celery_app.conf.imports = ["src.queue.tasks"]


def configure_celery():
    """Call this at application startup (FastAPI), not at import time."""
    from src.config import get_settings
    settings = get_settings()
    _apply_redis_config(settings.redis_url)
