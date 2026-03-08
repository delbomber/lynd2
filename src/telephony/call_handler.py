"""WebSocket call handler — orchestrates STT, TTS, and conversation state machine."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import WebSocket

from src.conversation.state_machine import ConversationContext, ConversationMachine
from src.conversation.states.identity import IdentityVerificationState
from src.conversation.states.introduction import IntroductionState
from src.conversation.states.prescreen import PreScreenState
from src.conversation.states.scheduling import SchedulingState
from src.conversation.states.escalation import EscalationState
from src.db.models import ConversationState, CallSession

logger = logging.getLogger(__name__)

# Twilio Media Streams sends mulaw 8kHz audio in 160-byte chunks (20ms)
MULAW_CHUNK_SIZE = 160

# Default pre-screen questions — override per study
DEFAULT_PRESCREEN_QUESTIONS = [
    {"key": "age_eligible", "text": "Are you between 18 and 70 years old?"},
    {"key": "diagnosis_confirmed", "text": "Have you been diagnosed with the condition your doctor referred you about?"},
    {"key": "no_conflicting_treatment", "text": "Are you currently free from any treatments that might interfere with a clinical study?"},
]


class CallHandler:
    """Orchestrates one real-time voice conversation over a Twilio Media Stream."""

    def __init__(
        self,
        context: ConversationContext,
        patient_dob: str,
        job_id: int,
        db,
        websocket: Optional[WebSocket] = None,
        deepgram_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        elevenlabs_voice_id: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        calendly_event_url: Optional[str] = None,
    ):
        self.context = context
        self.patient_dob = patient_dob
        self.job_id = job_id
        self.db = db
        self.websocket = websocket

        # Resolve config: use explicit values or fall back to settings
        if any(
            v is None
            for v in [
                deepgram_api_key,
                elevenlabs_api_key,
                elevenlabs_voice_id,
                anthropic_api_key,
            ]
        ):
            from src.config import get_settings

            settings = get_settings()
            deepgram_api_key = deepgram_api_key or settings.deepgram_api_key
            elevenlabs_api_key = elevenlabs_api_key or settings.elevenlabs_api_key
            elevenlabs_voice_id = elevenlabs_voice_id or settings.elevenlabs_voice_id
            anthropic_api_key = anthropic_api_key or settings.anthropic_api_key
            calendly_event_url = calendly_event_url or settings.calendly_event_url

        self.deepgram_api_key = deepgram_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.elevenlabs_voice_id = elevenlabs_voice_id
        self.anthropic_api_key = anthropic_api_key
        self.calendly_event_url = calendly_event_url or ""

        # State machine
        self.machine = ConversationMachine(context)

        # Conversation state handlers
        self.identity_state = IdentityVerificationState()
        self.introduction_state = IntroductionState()
        self.prescreen_state = PreScreenState(questions=DEFAULT_PRESCREEN_QUESTIONS)
        self.scheduling_state = SchedulingState(
            calendly_event_url=self.calendly_event_url
        )
        self.escalation_state = EscalationState()

        # Pre-screen tracking
        self.question_index = 0
        self.identity_attempt = 1

        # Twilio stream SID for sending audio back
        self.stream_sid: Optional[str] = None

        # STT / TTS are lazily initialized in run_websocket_session
        self.stt = None
        self.tts = None

    async def speak(self, text: str) -> None:
        """Synthesize text via TTS and stream audio chunks back to Twilio WebSocket."""
        self.context.append_transcript("agent", text)
        logger.info("Agent says: %s", text)

        if self.websocket is None or self.tts is None:
            return

        loop = asyncio.get_running_loop()
        mulaw_audio = await loop.run_in_executor(None, self.tts.synthesize, text)

        if not mulaw_audio:
            return

        # Send in 160-byte chunks (20ms at 8kHz mulaw)
        for offset in range(0, len(mulaw_audio), MULAW_CHUNK_SIZE):
            chunk = mulaw_audio[offset : offset + MULAW_CHUNK_SIZE]
            payload = base64.b64encode(chunk).decode("ascii")
            media_msg = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": payload},
            }
            await self.websocket.send_json(media_msg)

        # Send mark to signal end of speech
        mark_msg = {
            "event": "mark",
            "streamSid": self.stream_sid,
            "mark": {"name": "speech_done"},
        }
        await self.websocket.send_json(mark_msg)

    async def on_call_start(self) -> None:
        """Send the opening identity verification prompt."""
        prompt = self.identity_state.get_opening_prompt(self.context)
        await self.speak(prompt)

    async def on_transcript(self, text: str) -> None:
        """Route patient speech to the current state handler and transition."""
        self.context.append_transcript("patient", text)
        logger.info("Patient says: %s", text)

        current = self.machine.current_state

        if current == ConversationState.IDENTITY_VERIFICATION:
            next_state, response = self.identity_state.handle_response(
                patient_text=text,
                context=self.context,
                actual_dob=self.patient_dob,
                api_key=self.anthropic_api_key,
                attempt=self.identity_attempt,
            )
            self.identity_attempt += 1
            if next_state != current:
                self.machine.transition(next_state)

        elif current == ConversationState.INTRODUCTION:
            next_state, response = self.introduction_state.handle_response(
                patient_text=text,
                context=self.context,
                api_key=self.anthropic_api_key,
            )
            if next_state != current:
                self.machine.transition(next_state)

        elif current == ConversationState.PRE_SCREEN:
            next_state, response, meta = self.prescreen_state.handle_response(
                patient_text=text,
                context=self.context,
                question_index=self.question_index,
                api_key=self.anthropic_api_key,
            )
            if "next_question_index" in meta:
                self.question_index = meta["next_question_index"]
            if next_state != current:
                self.machine.transition(next_state)

        elif current == ConversationState.SCHEDULING:
            next_state, response = self.scheduling_state.handle_response(
                patient_text=text,
                context=self.context,
                api_key=self.anthropic_api_key,
            )
            if next_state != current:
                self.machine.transition(next_state)

        elif current == ConversationState.ESCALATION:
            response = self.escalation_state.get_handoff_message()
            self.machine.transition(ConversationState.COMPLETED)

        elif current == ConversationState.COMPLETED:
            response = "Thank you for your time. Goodbye."

        else:
            response = "I'm sorry, something went wrong."

        await self.speak(response)

    async def run_websocket_session(self) -> None:
        """Main loop: receive Twilio Media Stream messages and route audio to STT."""
        from src.audio.stt import DeepgramTranscriber
        from src.audio.tts import ElevenLabsTTS

        self.tts = ElevenLabsTTS(
            api_key=self.elevenlabs_api_key,
            voice_id=self.elevenlabs_voice_id,
        )
        self.stt = DeepgramTranscriber(api_key=self.deepgram_api_key)

        await self.stt.start(on_transcript=self.on_transcript)

        try:
            while True:
                raw = await self.websocket.receive_text()
                msg = json.loads(raw)
                event = msg.get("event")

                if event == "start":
                    self.stream_sid = msg["start"]["streamSid"]
                    logger.info(
                        "Media stream started: streamSid=%s", self.stream_sid
                    )
                    # Now that we have the streamSid, send the opening prompt
                    await self.on_call_start()

                elif event == "media":
                    audio_bytes = base64.b64decode(msg["media"]["payload"])
                    await self.stt.send_audio(audio_bytes)

                elif event == "stop":
                    logger.info("Media stream stopped")
                    break

        except Exception:
            logger.exception("WebSocket session error")
        finally:
            if self.stt:
                await self.stt.finish()
            await self._save_session()

    async def _save_session(self) -> None:
        """Persist final state and transcript to an existing CallSession."""
        try:
            session = self.db.query(CallSession).filter(
                CallSession.outreach_job_id == self.job_id
            ).first()
            if session:
                session.final_state = self.machine.current_state
                session.transcript = json.dumps(self.context.transcript_segments)
                session.ended_at = datetime.utcnow()
                self.db.commit()
            logger.info("Call session saved for job_id=%s", self.job_id)
        except Exception:
            logger.exception("Failed to save call session for job_id=%s", self.job_id)
