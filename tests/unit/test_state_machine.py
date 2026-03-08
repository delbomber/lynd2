import pytest
from src.conversation.state_machine import ConversationMachine, ConversationContext
from src.db.models import ConversationState


def test_machine_starts_in_identity_verification():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    assert machine.current_state == ConversationState.IDENTITY_VERIFICATION


def test_machine_transitions_to_introduction():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    machine.transition(ConversationState.INTRODUCTION)
    assert machine.current_state == ConversationState.INTRODUCTION


def test_machine_cannot_skip_states():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    with pytest.raises(ValueError, match="Invalid transition"):
        machine.transition(ConversationState.PRE_SCREEN)


def test_machine_can_always_escalate():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    machine.transition(ConversationState.ESCALATION)
    assert machine.current_state == ConversationState.ESCALATION


def test_machine_tracks_history():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    machine.transition(ConversationState.INTRODUCTION)
    machine.transition(ConversationState.PRE_SCREEN)
    assert len(machine.history) == 3


def test_can_transition_returns_true_for_valid():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    assert machine.can_transition(ConversationState.INTRODUCTION) is True
    assert machine.can_transition(ConversationState.PRE_SCREEN) is False


def test_context_stores_pre_screen_responses():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    ctx.record_response("age_eligible", "yes", "Yes, I am 45 years old")
    assert ctx.pre_screen_responses["age_eligible"]["value"] == "yes"


def test_context_appends_transcript():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    ctx.append_transcript("agent", "Hello Jane")
    ctx.append_transcript("patient", "Hi there")
    assert len(ctx.transcript_segments) == 2
    assert ctx.transcript_segments[0]["speaker"] == "agent"
