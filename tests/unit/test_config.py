def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15551234567")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg_key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el_key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_id")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant_key")
    monkeypatch.setenv("APP_BASE_URL", "https://test.lynd.com")

    from src.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.database_url == "postgresql://test:test@localhost/test"
    assert settings.twilio_account_sid == "ACtest"
    get_settings.cache_clear()  # clean up so other tests aren't affected
