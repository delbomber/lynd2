from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import get_settings


def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
