from src.queue.worker import celery_app


@celery_app.task(name="queue_outreach")
def queue_outreach(referral_id: int):
    """Schedules outreach jobs for a referral. Full implementation in Task 6."""
    pass


@celery_app.task(name="execute_outreach_job")
def execute_outreach_job(job_id: int):
    """Executes a single outreach attempt. Full implementation in Tasks 7, 17."""
    pass
