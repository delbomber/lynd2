from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    deepgram_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    anthropic_api_key: str
    calendly_api_key: str = ""
    calendly_event_url: str = ""
    app_base_url: str = "http://localhost:8000"
    environment: str = "development"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
