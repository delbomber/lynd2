import os
from celery import Celery

# Create celery app. If REDIS_URL is available at import time (worker process),
# configure immediately. For the FastAPI process, configure_celery() is called
# at startup to ensure settings are loaded.
celery_app = Celery("lynd")

# Auto-configure when running as standalone worker
if os.environ.get("REDIS_URL"):
    celery_app.conf.broker_url = os.environ["REDIS_URL"]
    celery_app.conf.result_backend = os.environ["REDIS_URL"]
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"

# Import tasks so they are registered with the app
celery_app.conf.imports = ["src.queue.tasks"]


def configure_celery():
    """Call this at application startup (FastAPI), not at import time."""
    from src.config import get_settings
    settings = get_settings()
    celery_app.conf.broker_url = settings.redis_url
    celery_app.conf.result_backend = settings.redis_url
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"
