from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@lru_cache(maxsize=1)
def _get_engine():
    from src.config import get_settings
    return create_engine(get_settings().database_url)


@lru_cache(maxsize=1)
def _get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())


def get_db():
    """FastAPI dependency that yields a database session."""
    SessionLocal = _get_session_factory()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
