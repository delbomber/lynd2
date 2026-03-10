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

        orch = OutreachOrchestrator(db=db, study_id=referral.study_id or "")
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


@celery_app.task(name="execute_outreach_job", max_retries=0)
def execute_outreach_job(job_id: int):
    """Executes a single outreach attempt — makes the Twilio call."""
    from src.db.session import _get_session_factory
    from src.db.models import OutreachJob, OutreachStatus, Referral, Patient, CallSession
    from src.telephony.client import TwilioClient
    from src.config import get_settings
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
        if not job or job.status in (
            OutreachStatus.CANCELLED,
            OutreachStatus.COMPLETED,
            OutreachStatus.IN_PROGRESS,
        ):
            logger.info("Skipping job %s (status=%s)", job_id, job.status if job else "not found")
            return

        referral = db.query(Referral).filter(Referral.id == job.referral_id).first()
        patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()

        job.status = OutreachStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        db.commit()

        if job.channel == "voice":
            # Pre-generate greeting audio with ElevenLabs before calling
            # so it plays instantly when the patient picks up
            from src.audio.tts import ElevenLabsTTS
            from src.audio.greeting_cache import cache_greeting_audio

            from src.conversation.states.identity import _expand_title
            provider = _expand_title(referral.referring_provider) if referral.referring_provider else "Your doctor"
            greeting_text = (
                f"Hi {patient.first_name}, this is Sarah calling from Lynd Clinical. "
                f"{provider} recently referred you to us about a research study, "
                f"and I'm calling to follow up. Is now an okay time?"
            )
            tts = ElevenLabsTTS(
                api_key=settings.elevenlabs_api_key,
                voice_id=settings.elevenlabs_voice_id,
            )
            logger.info("Pre-generating greeting audio for job %s", job_id)
            mp3_audio = tts.synthesize_mp3(greeting_text)
            if mp3_audio:
                cache_greeting_audio(job_id, mp3_audio, redis_url=settings.redis_url)
                logger.info("Greeting audio cached for job %s (%d bytes)", job_id, len(mp3_audio))

            twilio = TwilioClient(
                account_sid=settings.twilio_account_sid,
                auth_token=settings.twilio_auth_token,
                from_number=settings.twilio_phone_number,
            )
            base_url = settings.app_base_url
            call_sid = twilio.make_outbound_call(
                to=patient.phone,
                webhook_url=f"{base_url}/webhooks/call/{job_id}/answer",
                status_callback_url=f"{base_url}/webhooks/call/{job_id}/status",
            )
            # Create CallSession so webhooks can update it
            call_session = CallSession(
                outreach_job_id=job_id,
                twilio_call_sid=call_sid,
                started_at=datetime.utcnow(),
            )
            db.add(call_session)
            db.commit()

        elif job.channel == "sms":
            twilio = TwilioClient(
                account_sid=settings.twilio_account_sid,
                auth_token=settings.twilio_auth_token,
                from_number=settings.twilio_phone_number,
            )
            twilio.send_sms(
                to=patient.phone,
                body=(
                    f"Hi {patient.first_name}, this is Lynd Clinical. "
                    f"Your provider referred you for a research opportunity. "
                    f"We tried to reach you by phone. Please call us back at "
                    f"{settings.twilio_phone_number} if you're interested."
                ),
            )
            job.status = OutreachStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.exception("execute_outreach_job failed for job_id=%s", job_id)
        try:
            if job:
                job.status = OutreachStatus.FAILED
                db.commit()
        except Exception:
            logger.exception("Failed to mark job %s as FAILED", job_id)
    finally:
        db.close()
