import pytest
from unittest.mock import patch, MagicMock

from src.conversation.states.introduction import IntroductionState
from src.conversation.states.prescreen import PreScreenState
from src.conversation.states.scheduling import SchedulingState
from src.conversation.states.escalation import EscalationState
from src.conversation.state_machine import ConversationContext
from src.db.models import ConversationState
from src.llm.intent import Intent


def make_context():
    return ConversationContext(patient_name="Jane Doe", study_id="STUDY-001")


# --- Introduction ---


def test_introduction_has_opening_prompt():
    state = IntroductionState()
    prompt = state.get_opening_prompt(make_context())
    assert "Lynd Clinical" in prompt or "research" in prompt.lower()


def test_introduction_advances_on_interest():
    state = IntroductionState()
    ctx = make_context()
    with patch("src.conversation.states.introduction.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CONFIRM
        next_state, _ = state.handle_response("Yes I'm interested", ctx, api_key="test")
    assert next_state == ConversationState.PRE_SCREEN
    assert ctx.interest_level == "interested"


def test_introduction_completes_on_not_interested():
    state = IntroductionState()
    ctx = make_context()
    with patch("src.conversation.states.introduction.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.DENY
        next_state, response = state.handle_response("No thank you", ctx, api_key="test")
    assert next_state == ConversationState.COMPLETED
    assert ctx.interest_level == "not_interested"


def test_introduction_escalates_on_request():
    state = IntroductionState()
    ctx = make_context()
    with patch("src.conversation.states.introduction.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.ESCALATE
        next_state, _ = state.handle_response("Let me talk to someone", ctx, api_key="test")
    assert next_state == ConversationState.ESCALATION


# --- Pre-Screen ---


def test_prescreen_captures_structured_response():
    state = PreScreenState(questions=[
        {"key": "age_eligible", "text": "Are you between 18 and 70 years old?"},
        {"key": "diagnosis", "text": "Have you been diagnosed with the condition?"},
    ])
    ctx = make_context()
    with patch("src.conversation.states.prescreen.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CONFIRM
        next_state, response, extras = state.handle_response("Yes I am 45", ctx, question_index=0, api_key="test")
    assert ctx.pre_screen_responses["age_eligible"]["value"] == "yes"
    assert next_state == ConversationState.PRE_SCREEN  # still has more questions


def test_prescreen_advances_to_scheduling_after_last_question():
    state = PreScreenState(questions=[
        {"key": "age_eligible", "text": "Are you between 18 and 70?"},
    ])
    ctx = make_context()
    with patch("src.conversation.states.prescreen.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CONFIRM
        next_state, _, _ = state.handle_response("Yes", ctx, question_index=0, api_key="test")
    assert next_state == ConversationState.SCHEDULING


def test_prescreen_escalates_on_request():
    state = PreScreenState(questions=[
        {"key": "age_eligible", "text": "Are you between 18 and 70?"},
    ])
    ctx = make_context()
    with patch("src.conversation.states.prescreen.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.ESCALATE
        next_state, _, _ = state.handle_response("I have a medical question", ctx, question_index=0, api_key="test")
    assert next_state == ConversationState.ESCALATION


# --- Scheduling ---


def test_scheduling_completes_on_schedule():
    state = SchedulingState(calendly_event_url="https://calendly.com/lynd/screening")
    ctx = make_context()
    with patch("src.conversation.states.scheduling.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.SCHEDULE
        next_state, response = state.handle_response("I'd like to schedule", ctx, api_key="test")
    assert next_state == ConversationState.COMPLETED
    assert ctx.scheduling_outcome == "scheduled"


def test_scheduling_handles_callback():
    state = SchedulingState(calendly_event_url="https://calendly.com/lynd/screening")
    ctx = make_context()
    with patch("src.conversation.states.scheduling.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CALLBACK
        next_state, _ = state.handle_response("Call me back later", ctx, api_key="test")
    assert next_state == ConversationState.COMPLETED
    assert ctx.scheduling_outcome == "callback_requested"


def test_scheduling_handles_decline():
    state = SchedulingState(calendly_event_url="https://calendly.com/lynd/screening")
    ctx = make_context()
    with patch("src.conversation.states.scheduling.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.DENY
        next_state, _ = state.handle_response("No thanks", ctx, api_key="test")
    assert next_state == ConversationState.COMPLETED
    assert ctx.scheduling_outcome == "declined"


# --- Escalation ---


def test_escalation_returns_handoff_message():
    state = EscalationState()
    msg = state.get_handoff_message()
    assert "study team" in msg.lower() or "coordinator" in msg.lower()
