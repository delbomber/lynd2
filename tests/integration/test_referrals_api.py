import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.api.dependencies import get_db

client = TestClient(app)


def test_create_referral_returns_201():
    mock_session = MagicMock()
    mock_session.flush.side_effect = lambda: None
    mock_session.refresh.side_effect = (
        lambda obj: setattr(obj, 'id', 1)
        or setattr(obj, 'status', MagicMock(value='pending'))
    )

    def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("src.api.routes.referrals.queue_outreach") as mock_queue:
        mock_queue.delay = MagicMock()

        payload = {
            "patient": {
                "first_name": "Jane",
                "last_name": "Doe",
                "phone": "+15551234567",
                "date_of_birth": "1980-01-15",
            },
            "study_id": "STUDY-001",
            "referring_provider": "Dr. Smith",
        }
        response = client.post("/api/v1/referrals", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert "referral_id" in response.json()


def test_create_referral_missing_phone_returns_422():
    payload = {
        "patient": {"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1980-01-15"},
        "study_id": "STUDY-001",
    }
    response = client.post("/api/v1/referrals", json=payload)
    assert response.status_code == 422
