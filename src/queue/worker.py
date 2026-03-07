from celery import Celery

# Create celery app with no broker configured at import time.
# Call configure_celery() at application startup to apply settings.
celery_app = Celery("lynd")


def configure_celery():
    """Call this at application startup, not at import time."""
    from src.config import get_settings
    settings = get_settings()
    celery_app.conf.broker_url = settings.redis_url
    celery_app.conf.result_backend = settings.redis_url
    celery_app.conf.task_serializer = "json"
    celery_app.conf.result_serializer = "json"
