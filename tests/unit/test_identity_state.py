import pytest
from unittest.mock import patch, MagicMock

from src.conversation.states.identity import (
    IdentityVerificationState,
    _looks_like_dob,
    MAX_DOB_ATTEMPTS,
)
from src.conversation.state_machine import ConversationContext
from src.db.models import ConversationState


def make_context():
    return ConversationContext(patient_name="Jane Doe", study_id="STUDY-001")


def test_opening_prompt_includes_patient_name():
    state = IdentityVerificationState()
    ctx = make_context()
    prompt = state.get_opening_prompt(ctx)
    assert "Jane" in prompt
    assert "date of birth" in prompt.lower()


def test_verify_dob_correct(monkeypatch):
    state = IdentityVerificationState()
    with patch("src.conversation.states.identity.ClaudeClient") as MockClaude:
        MockClaude.return_value.complete.return_value = "1980-01-15"
        result = state.verify_dob("January 15, 1980", "1980-01-15", api_key="test")
    assert result is True


def test_verify_dob_wrong(monkeypatch):
    state = IdentityVerificationState()
    with patch("src.conversation.states.identity.ClaudeClient") as MockClaude:
        MockClaude.return_value.complete.return_value = "1985-03-05"
        result = state.verify_dob("March 5, 1985", "1980-01-15", api_key="test")
    assert result is False


def test_handle_response_success():
    state = IdentityVerificationState()
    ctx = make_context()
    with patch.object(state, "verify_dob", return_value=True):
        next_state, response = state.handle_response(
            patient_text="January 15, 1980",
            context=ctx,
            actual_dob="1980-01-15",
            api_key="test",
        )
    assert next_state == ConversationState.INTRODUCTION
    assert ctx.identity_verified is True


def test_handle_response_retry_on_first_failure():
    state = IdentityVerificationState()
    ctx = make_context()
    with patch.object(state, "verify_dob", return_value=False):
        next_state, response = state.handle_response(
            patient_text="March 5 1999",
            context=ctx,
            actual_dob="1980-01-15",
            api_key="test",
            attempt=1,
        )
    assert next_state == ConversationState.IDENTITY_VERIFICATION
    assert "try again" in response.lower() or "match" in response.lower()


def test_handle_response_escalates_after_max_failures():
    state = IdentityVerificationState()
    ctx = make_context()
    with patch.object(state, "verify_dob", return_value=False):
        next_state, response = state.handle_response(
            patient_text="March 5 1999",
            context=ctx,
            actual_dob="1980-01-15",
            api_key="test",
            attempt=MAX_DOB_ATTEMPTS,
        )
    assert next_state == ConversationState.ESCALATION


def test_handle_response_retries_at_attempt_2():
    """With MAX_DOB_ATTEMPTS=3, attempt 2 should still retry."""
    state = IdentityVerificationState()
    ctx = make_context()
    with patch.object(state, "verify_dob", return_value=False):
        next_state, response = state.handle_response(
            patient_text="March 5 1999",
            context=ctx,
            actual_dob="1980-01-15",
            api_key="test",
            attempt=2,
        )
    assert next_state == ConversationState.IDENTITY_VERIFICATION


def test_non_dob_noise_not_counted_as_attempt():
    """Background noise like 'Miss Hurd' should not be treated as a DOB attempt."""
    state = IdentityVerificationState()
    ctx = make_context()
    next_state, response = state.handle_response(
        patient_text="Miss Hurd",
        context=ctx,
        actual_dob="1980-01-15",
        api_key="test",
        attempt=1,
    )
    assert next_state == ConversationState.IDENTITY_VERIFICATION
    assert "date of birth" in response.lower()


def test_looks_like_dob_with_digits():
    assert _looks_like_dob("12/01/1982") is True
    assert _looks_like_dob("december 1st 1982") is True
    assert _looks_like_dob("January 15, 1980") is True


def test_looks_like_dob_rejects_noise():
    assert _looks_like_dob("Miss Hurd") is False
    assert _looks_like_dob("hello") is False
    assert _looks_like_dob("yes this is Jane") is False
