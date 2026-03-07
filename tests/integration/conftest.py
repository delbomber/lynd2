"""
Integration test configuration.
Patches get_settings so tests run without a real .env file or external services.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True, scope="module")
def mock_settings():
    """Provide fake settings for the entire integration test session."""
    fake = MagicMock()
    fake.database_url = "sqlite:///./test.db"
    fake.redis_url = "redis://localhost:6379/0"
    fake.twilio_account_sid = "ACtest"
    fake.twilio_auth_token = "authtest"
    fake.twilio_phone_number = "+15550000000"
    fake.deepgram_api_key = "dg-test"
    fake.elevenlabs_api_key = "el-test"
    fake.elevenlabs_voice_id = "voice-test"
    fake.anthropic_api_key = "sk-test"
    fake.calendly_api_key = ""
    fake.calendly_event_url = ""
    fake.app_base_url = "http://localhost:8000"
    fake.environment = "test"

    with patch("src.config.get_settings", return_value=fake), \
         patch("src.db.session.get_settings", return_value=fake, create=True):
        yield fake
