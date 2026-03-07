from fastapi import APIRouter, Depends, Form, Response
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
