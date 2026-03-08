from fastapi import APIRouter, Depends, Form, Response, WebSocket
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from src.api.dependencies import get_db
from src.config import get_settings

router = APIRouter()

VOICEMAIL_MESSAGE = (
    "Hi, this is Lynd Clinical calling about a research opportunity "
    "your provider referred you for. We'll try again shortly. "
    "Thank you and have a great day."
)


@router.post("/call/{job_id}/answer")
async def handle_call_answer(
    job_id: int,
    CallSid: str = Form(...),
    AnsweredBy: str = Form(default="human"),
    To: str = Form(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    response = VoiceResponse()

    if AnsweredBy and AnsweredBy.startswith("machine"):
        # Voicemail — leave message with no PHI, then hang up
        response.say(VOICEMAIL_MESSAGE, voice="Polly.Joanna")
        response.hangup()
    else:
        # Human answered — connect to media stream for real-time conversation
        host = settings.app_base_url.replace("https://", "").replace("http://", "")
        connect = Connect()
        stream = Stream(url=f"wss://{host}/webhooks/stream/{job_id}")
        connect.append(stream)
        response.append(connect)

    return Response(content=str(response), media_type="application/xml")


@router.post("/call/{job_id}/status")
async def handle_call_status(
    job_id: int,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(default="0"),
    db: Session = Depends(get_db),
):
    """Records final call status. Updates CallSession if it exists."""
    from src.db.models import CallSession, CallOutcome
    from datetime import datetime

    outcome_map = {
        "completed": CallOutcome.ANSWERED,
        "no-answer": CallOutcome.NO_ANSWER,
        "busy": CallOutcome.BUSY,
        "failed": CallOutcome.FAILED,
    }

    session = db.query(CallSession).filter(CallSession.twilio_call_sid == CallSid).first()
    if session:
        session.outcome = outcome_map.get(CallStatus, CallOutcome.FAILED)
        session.duration_seconds = int(CallDuration)
        session.ended_at = datetime.utcnow()
        db.commit()

    return Response(content="<Response/>", media_type="application/xml")


@router.websocket("/stream/{job_id}")
async def handle_media_stream(job_id: int, websocket: WebSocket):
    """Twilio Media Streams WebSocket — real-time voice conversation."""
    await websocket.accept()

    from src.db.session import get_db as _get_db_gen
    from src.telephony.call_handler import CallHandler
    from src.conversation.state_machine import ConversationContext
    from src.db.models import OutreachJob, Patient, Referral

    db_gen = _get_db_gen()
    db = next(db_gen)
    try:
        job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
        if not job:
            await websocket.close()
            return

        referral = db.query(Referral).filter(Referral.id == job.referral_id).first()
        patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()

        context = ConversationContext(
            patient_name=f"{patient.first_name} {patient.last_name}",
            study_id=referral.study_id,
        )
        handler = CallHandler(
            context=context,
            patient_dob=patient.date_of_birth,
            job_id=job_id,
            db=db,
            websocket=websocket,
        )
        await handler.run_websocket_session()
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
