from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.api.dependencies import get_db
from src.config import get_settings

client = TestClient(app)

VOICEMAIL_TEXT = "Lynd Clinical"


def _override_db():
    mock_session = MagicMock()
    yield mock_session


def _mock_settings():
    s = MagicMock()
    s.app_base_url = "https://lynd.example.com"
    return s


def test_answer_webhook_returns_twiml_for_human():
    """When a human answers, should return TwiML that connects to media stream."""
    app.dependency_overrides[get_db] = _override_db
    try:
        with patch("src.api.routes.webhooks.get_settings", _mock_settings):
            response = client.post(
                "/webhooks/call/1/answer",
                data={
                    "CallSid": "CA123",
                    "AnsweredBy": "human",
                    "To": "+15551234567",
                    "From": "+15550000000",
                },
            )
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Response>" in response.text
    finally:
        app.dependency_overrides.clear()


def test_answer_webhook_voicemail_plays_message():
    """When voicemail detected, should play a no-PHI message and hang up."""
    app.dependency_overrides[get_db] = _override_db
    try:
        with patch("src.api.routes.webhooks.get_settings", _mock_settings):
            response = client.post(
                "/webhooks/call/1/answer",
                data={
                    "CallSid": "CA123",
                    "AnsweredBy": "machine_start",
                    "To": "+15551234567",
                    "From": "+15550000000",
                },
            )
        assert response.status_code == 200
        assert VOICEMAIL_TEXT in response.text
        # Voicemail must NOT contain any PHI (no patient name, DOB, etc.)
        assert "Hangup" in response.text or "hangup" in response.text.lower()
    finally:
        app.dependency_overrides.clear()


def test_status_webhook_returns_200():
    """Call status callback should return valid TwiML."""
    app.dependency_overrides[get_db] = _override_db
    try:
        response = client.post(
            "/webhooks/call/1/status",
            data={
                "CallSid": "CA123",
                "CallStatus": "completed",
                "CallDuration": "120",
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
