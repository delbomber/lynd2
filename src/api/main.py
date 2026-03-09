import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import referrals, webhooks
from src.queue.worker import configure_celery

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_celery()
    yield


app = FastAPI(title="Lynd Recruitment Voice Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(referrals.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/audio/greeting/{job_id}")
def serve_greeting_audio(job_id: int):
    """Serve pre-generated ElevenLabs greeting audio for Twilio <Play>."""
    from fastapi.responses import Response as FastAPIResponse
    from src.audio.greeting_cache import get_greeting_audio
    from src.config import get_settings

    settings = get_settings()
    audio = get_greeting_audio(job_id, redis_url=settings.redis_url)
    if not audio:
        return FastAPIResponse(status_code=404, content="Audio not found")
    return FastAPIResponse(content=audio, media_type="audio/mpeg")


@app.post("/admin/purge-queue")
def purge_queue():
    """Purge all pending Celery tasks from the queue."""
    from src.queue.worker import celery_app
    purged = celery_app.control.purge()
    return {"status": "purged", "tasks_removed": purged}


@app.post("/admin/cancel-all-jobs")
def cancel_all_jobs():
    """Cancel all queued/in-progress outreach jobs in the database.

    This ensures that even if delayed Celery tasks fire, the worker
    will skip them because the job status is CANCELLED.
    """
    from src.api.dependencies import get_db
    from src.db.models import OutreachJob, OutreachStatus

    db = next(get_db())
    try:
        cancelled = (
            db.query(OutreachJob)
            .filter(OutreachJob.status.in_([
                OutreachStatus.QUEUED,
                OutreachStatus.IN_PROGRESS,
            ]))
            .update(
                {OutreachJob.status: OutreachStatus.CANCELLED},
                synchronize_session="fetch",
            )
        )
        db.commit()

        # Also purge the Celery queue
        from src.queue.worker import celery_app
        celery_app.control.purge()

        return {"status": "cancelled", "jobs_cancelled": cancelled}
    finally:
        db.close()
