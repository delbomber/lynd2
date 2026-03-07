from src.queue.worker import celery_app


@celery_app.task(name="queue_outreach")
def queue_outreach(referral_id: int):
    """Creates outreach jobs for a referral and schedules them."""
    from src.db.session import _get_session_factory
    from src.db.models import Referral
    from src.outreach.orchestrator import OutreachOrchestrator

    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        referral = db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            return

        orch = OutreachOrchestrator(db=db)
        jobs = orch.create_outreach_jobs(referral)

        for job in jobs:
            # Schedule each job with appropriate countdown
            delay_seconds = max(0, (job.scheduled_at - __import__("datetime").datetime.utcnow()).total_seconds())
            execute_outreach_job.apply_async(
                args=[job.id],
                countdown=int(delay_seconds),
            )
    finally:
        db.close()


@celery_app.task(name="execute_outreach_job")
def execute_outreach_job(job_id: int):
    """Executes a single outreach attempt. Full implementation in Tasks 7, 17."""
    pass
