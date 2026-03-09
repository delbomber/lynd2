import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.telephony.call_handler import CallHandler
from src.conversation.state_machine import ConversationContext, ConversationMachine
from src.db.models import ConversationState


def _make_handler(**overrides):
    """Create a CallHandler with dummy config values so get_settings() is never called."""
    defaults = dict(
        context=ConversationContext(patient_name="Jane Doe", study_id="STUDY-001"),
        patient_dob="1980-01-15",
        job_id=1,
        db=MagicMock(),
        deepgram_api_key="test-dg-key",
        elevenlabs_api_key="test-el-key",
        elevenlabs_voice_id="test-voice-id",
        anthropic_api_key="test-anthropic-key",
        calendly_event_url="https://calendly.example.com/test",
    )
    defaults.update(overrides)
    return CallHandler(**defaults)


@pytest.mark.asyncio
async def test_call_handler_initializes_state_machine():
    handler = _make_handler()
    assert handler.machine.current_state == ConversationState.IDENTITY_VERIFICATION


@pytest.mark.asyncio
async def test_call_handler_logs_opening_prompt():
    handler = _make_handler()
    await handler.on_call_start()
    # Opening greeting is now played by Twilio TTS, but still recorded in transcript
    assert len(handler.context.transcript_segments) == 1
    assert handler.context.transcript_segments[0]["speaker"] == "agent"
    assert "Jane" in handler.context.transcript_segments[0]["text"]


@pytest.mark.asyncio
async def test_call_handler_routes_transcript_to_current_state():
    handler = _make_handler()
    with patch.object(handler, "speak", new_callable=AsyncMock), \
         patch.object(handler.identity_state, "handle_response") as mock_handle:
        mock_handle.return_value = (ConversationState.INTRODUCTION, "Thank you")
        await handler.on_transcript("January 15, 1980")
        mock_handle.assert_called_once()


@pytest.mark.asyncio
async def test_call_handler_transitions_state_on_identity_success():
    handler = _make_handler()
    with patch.object(handler, "speak", new_callable=AsyncMock), \
         patch.object(handler.identity_state, "handle_response") as mock_handle:
        mock_handle.return_value = (ConversationState.INTRODUCTION, "Thank you")
        await handler.on_transcript("January 15, 1980")
        assert handler.machine.current_state == ConversationState.INTRODUCTION


@pytest.mark.asyncio
async def test_call_handler_stays_in_state_on_retry():
    handler = _make_handler()
    with patch.object(handler, "speak", new_callable=AsyncMock), \
         patch.object(handler.identity_state, "handle_response") as mock_handle:
        mock_handle.return_value = (
            ConversationState.IDENTITY_VERIFICATION,
            "Could you try again?",
        )
        await handler.on_transcript("uh what")
        assert handler.machine.current_state == ConversationState.IDENTITY_VERIFICATION


@pytest.mark.asyncio
async def test_call_handler_records_transcript():
    handler = _make_handler()
    with patch.object(handler, "speak", new_callable=AsyncMock), \
         patch.object(handler.identity_state, "handle_response") as mock_handle:
        mock_handle.return_value = (ConversationState.INTRODUCTION, "Thank you")
        await handler.on_transcript("January 15, 1980")
        # on_transcript appends patient transcript, speak appends agent transcript
        speakers = [seg["speaker"] for seg in handler.context.transcript_segments]
        assert "patient" in speakers
