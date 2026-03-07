# Recruitment Voice Agent V1 – Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated outreach system that contacts referred clinical trial patients by phone immediately after referral, conducts a structured pre-screen, and captures all interaction data for continuous improvement.

**Architecture:** Referrals arrive via API, trigger jobs in a Celery queue, which initiate Twilio outbound calls. Patient audio is streamed in real-time to Deepgram (speech-to-text), routed through a state-machine conversation engine backed by Claude for intent detection and ElevenLabs for speech synthesis. All interactions are stored in PostgreSQL. Failed calls fall back to SMS.

**Tech Stack:** Python 3.11, FastAPI, PostgreSQL + pgvector (AWS RDS), Redis (AWS ElastiCache), Celery, Twilio (voice + SMS), Deepgram (STT), ElevenLabs (TTS), Claude API (claude-sonnet-4-6), Calendly API, Docker, AWS ECS Fargate

---

## Timeline Risk

- Week 1: Tasks 1–8 (foundation + telephony)
- Week 2: Tasks 9–15 (conversation engine)
- Week 3: Tasks 16–21 (guardrails + outreach logic + data capture)
- Week 4: Tasks 22–24 (analytics + coordinator tools + pilot prep)

**Risks:** Real-time audio streaming (Task 9) is the highest-risk component. If Twilio Media Streams + Deepgram latency is unacceptable, fallback to Twilio `<Gather>` with speech recognition for V1 (simpler but less responsive). Flag this at end of Task 10.

---

## Project Structure

```
lynd2/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── referrals.py
│   │       └── webhooks.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── worker.py
│   │   └── tasks.py
│   ├── telephony/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── call_handler.py
│   │   └── sms.py
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── stt.py
│   │   └── tts.py
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── state_machine.py
│   │   └── states/
│   │       ├── __init__.py
│   │       ├── identity.py
│   │       ├── introduction.py
│   │       ├── prescreen.py
│   │       ├── scheduling.py
│   │       └── escalation.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── intent.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py
│   │   └── retrieval.py
│   └── outreach/
│       ├── __init__.py
│       └── orchestrator.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── docs/
│   └── plans/
├── scripts/
│   └── ingest_irb_script.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `src/api/__init__.py`, `src/api/main.py`
- Create all `__init__.py` files in the structure above

**Step 1: Create pyproject.toml**

```toml
[project]
name = "lynd2"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pgvector>=0.2.4",
    "celery[redis]>=5.3.6",
    "redis>=5.0.1",
    "twilio>=8.12.0",
    "deepgram-sdk>=3.2.0",
    "elevenlabs>=1.0.0",
    "anthropic>=0.20.0",
    "httpx>=0.26.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "httpx>=0.26.0",
    "ruff>=0.2.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: lynd
      POSTGRES_USER: lynd
      POSTGRES_PASSWORD: lynd_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://lynd:lynd_dev@postgres:5432/lynd
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: .
    environment:
      DATABASE_URL: postgresql://lynd:lynd_dev@postgres:5432/lynd
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: celery -A src.queue.worker worker --loglevel=info

volumes:
  postgres_data:
```

**Step 3: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pip-tools

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

ENV PYTHONPATH=/app
```

**Step 4: Create .env.example**

```env
# Database
DATABASE_URL=postgresql://lynd:lynd_dev@localhost:5432/lynd

# Redis
REDIS_URL=redis://localhost:6379/0

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Deepgram
DEEPGRAM_API_KEY=

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Anthropic
ANTHROPIC_API_KEY=

# Calendly
CALENDLY_API_KEY=
CALENDLY_EVENT_URL=

# App
APP_BASE_URL=https://your-domain.com
ENVIRONMENT=development
```

**Step 5: Create src/api/main.py**

```python
from fastapi import FastAPI
from src.api.routes import referrals, webhooks

app = FastAPI(title="Lynd Recruitment Voice Agent", version="0.1.0")

app.include_router(referrals.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 6: Create all empty `__init__.py` files**

Run:
```bash
find src tests -type d | xargs -I{} touch {}/__init__.py
mkdir -p tests/unit tests/integration
```

**Step 7: Verify app starts**

```bash
docker-compose up postgres redis -d
pip install -e ".[dev]"
uvicorn src.api.main:app --reload
```

Expected: Server starts at http://localhost:8000, `/health` returns `{"status": "ok"}`

---

## Task 2: Configuration & Settings

**Files:**
- Create: `src/config.py`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_config.py
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
    settings = get_settings()
    assert settings.database_url == "postgresql://test:test@localhost/test"
    assert settings.twilio_account_sid == "ACtest"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

```python
# src/config.py
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold with config"
```

---

## Task 3: Database Models

**Files:**
- Create: `src/db/models.py`
- Create: `src/db/session.py`
- Test: `tests/unit/test_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_models.py
from src.db.models import Patient, Referral, OutreachJob, CallSession, PreScreenResponse, AuditLog
from src.db.models import OutreachStatus, CallOutcome, ConversationState

def test_patient_model_has_required_fields():
    p = Patient(
        first_name="Jane",
        last_name="Doe",
        phone="+15551234567",
        date_of_birth="1980-01-01",
    )
    assert p.first_name == "Jane"
    assert p.phone == "+15551234567"

def test_referral_model_has_status():
    from src.db.models import ReferralStatus
    assert ReferralStatus.PENDING == "pending"
    assert ReferralStatus.COMPLETED == "completed"

def test_outreach_job_links_to_referral():
    job = OutreachJob(referral_id=1, attempt_number=1, status=OutreachStatus.QUEUED)
    assert job.attempt_number == 1
    assert job.status == OutreachStatus.QUEUED
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement**

```python
# src/db/models.py
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean,
    ForeignKey, JSON, Enum as SQLEnum, Float
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ReferralStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OutreachStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallOutcome(str, enum.Enum):
    ANSWERED = "answered"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"


class ConversationState(str, enum.Enum):
    IDENTITY_VERIFICATION = "identity_verification"
    INTRODUCTION = "introduction"
    PRE_SCREEN = "pre_screen"
    SCHEDULING = "scheduling"
    ESCALATION = "escalation"
    COMPLETED = "completed"


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    date_of_birth = Column(String(10), nullable=False)  # stored as YYYY-MM-DD string
    email = Column(String(200))
    communication_preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    referrals = relationship("Referral", back_populates="patient")


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    study_id = Column(String(100), nullable=False)
    referring_provider = Column(String(200))
    referral_metadata = Column(JSON, default={})
    status = Column(SQLEnum(ReferralStatus), default=ReferralStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    patient = relationship("Patient", back_populates="referrals")
    outreach_jobs = relationship("OutreachJob", back_populates="referral")


class OutreachJob(Base):
    __tablename__ = "outreach_jobs"
    id = Column(Integer, primary_key=True)
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    channel = Column(String(20), default="voice")  # voice or sms
    status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.QUEUED)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    celery_task_id = Column(String(200))
    referral = relationship("Referral", back_populates="outreach_jobs")
    call_sessions = relationship("CallSession", back_populates="outreach_job")


class CallSession(Base):
    __tablename__ = "call_sessions"
    id = Column(Integer, primary_key=True)
    outreach_job_id = Column(Integer, ForeignKey("outreach_jobs.id"), nullable=False)
    twilio_call_sid = Column(String(100), unique=True)
    outcome = Column(SQLEnum(CallOutcome))
    duration_seconds = Column(Integer)
    recording_url = Column(String(500))
    transcript = Column(Text)
    final_state = Column(SQLEnum(ConversationState))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    outreach_job = relationship("OutreachJob", back_populates="call_sessions")
    pre_screen_responses = relationship("PreScreenResponse", back_populates="call_session")


class PreScreenResponse(Base):
    __tablename__ = "pre_screen_responses"
    id = Column(Integer, primary_key=True)
    call_session_id = Column(Integer, ForeignKey("call_sessions.id"), nullable=False)
    question_key = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    response_text = Column(Text)
    response_value = Column(String(200))  # structured value (yes/no/date/etc)
    captured_at = Column(DateTime, default=datetime.utcnow)
    call_session = relationship("CallSession", back_populates="pre_screen_responses")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)  # referral, call_session, etc
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 4: Create session.py**

```python
# src/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_models.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/db/ tests/unit/test_models.py
git commit -m "feat: database models for patient, referral, call, pre-screen, audit"
```

---

## Task 4: Alembic Migrations

**Files:**
- Create: `src/db/migrations/` (alembic structure)
- Create: `alembic.ini`

**Step 1: Initialize alembic**

```bash
alembic init src/db/migrations
```

**Step 2: Update alembic.ini**

Change `sqlalchemy.url` line to:
```ini
sqlalchemy.url = %(DATABASE_URL)s
```

**Step 3: Update src/db/migrations/env.py**

Replace the `target_metadata` section:
```python
import os
from src.db.models import Base
target_metadata = Base.metadata

# In run_migrations_offline and run_migrations_online, use:
# url = os.environ["DATABASE_URL"]
```

Full env.py `run_migrations_online` function:
```python
def run_migrations_online() -> None:
    import os
    from sqlalchemy import engine_from_config, pool
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = os.environ["DATABASE_URL"]
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

**Step 4: Generate and run initial migration**

```bash
docker-compose up postgres -d
DATABASE_URL=postgresql://lynd:lynd_dev@localhost:5432/lynd alembic revision --autogenerate -m "initial schema"
DATABASE_URL=postgresql://lynd:lynd_dev@localhost:5432/lynd alembic upgrade head
```

Expected: Tables created, no errors

**Step 5: Verify tables exist**

```bash
docker-compose exec postgres psql -U lynd -d lynd -c "\dt"
```

Expected: Lists patients, referrals, outreach_jobs, call_sessions, pre_screen_responses, audit_logs

**Step 6: Commit**

```bash
git add alembic.ini src/db/migrations/
git commit -m "feat: alembic migration setup with initial schema"
```

---

## Task 5: Referral Intake API

**Files:**
- Create: `src/api/routes/referrals.py`
- Create: `src/api/dependencies.py`
- Test: `tests/integration/test_referrals_api.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_referrals_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app

client = TestClient(app)

def test_create_referral_returns_201():
    with patch("src.api.routes.referrals.get_db") as mock_db, \
         patch("src.api.routes.referrals.queue_outreach") as mock_queue:
        mock_session = MagicMock()
        mock_db.return_value = iter([mock_session])
        mock_queue.return_value = None

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
        assert response.status_code == 201
        assert "referral_id" in response.json()

def test_create_referral_missing_phone_returns_422():
    payload = {
        "patient": {"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1980-01-15"},
        "study_id": "STUDY-001",
    }
    response = client.post("/api/v1/referrals", json=payload)
    assert response.status_code == 422
```

**Step 2: Run to verify it fails**

```bash
pytest tests/integration/test_referrals_api.py -v
```

Expected: FAIL with routing errors

**Step 3: Create dependencies.py**

```python
# src/api/dependencies.py
from src.db.session import get_db

__all__ = ["get_db"]
```

**Step 4: Create referrals route**

```python
# src/api/routes/referrals.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.api.dependencies import get_db
from src.db.models import Patient, Referral, ReferralStatus
from src.queue.tasks import queue_outreach

router = APIRouter()


class PatientInput(BaseModel):
    first_name: str
    last_name: str
    phone: str
    date_of_birth: str
    email: str | None = None
    communication_preferences: dict = {}


class ReferralInput(BaseModel):
    patient: PatientInput
    study_id: str
    referring_provider: str | None = None
    referral_metadata: dict = {}


class ReferralResponse(BaseModel):
    referral_id: int
    status: str


@router.post("/referrals", status_code=201, response_model=ReferralResponse)
def create_referral(payload: ReferralInput, db: Session = Depends(get_db)):
    patient = Patient(
        first_name=payload.patient.first_name,
        last_name=payload.patient.last_name,
        phone=payload.patient.phone,
        date_of_birth=payload.patient.date_of_birth,
        email=payload.patient.email,
        communication_preferences=payload.patient.communication_preferences,
    )
    db.add(patient)
    db.flush()

    referral = Referral(
        patient_id=patient.id,
        study_id=payload.study_id,
        referring_provider=payload.referring_provider,
        referral_metadata=payload.referral_metadata,
        status=ReferralStatus.PENDING,
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)

    queue_outreach.delay(referral.id)

    return ReferralResponse(referral_id=referral.id, status=referral.status.value)
```

**Step 5: Create stub queue tasks (to unblock tests)**

```python
# src/queue/tasks.py
from src.queue.worker import celery_app


@celery_app.task(name="queue_outreach")
def queue_outreach(referral_id: int):
    # Implemented in Task 7
    pass
```

```python
# src/queue/worker.py
from celery import Celery
from src.config import get_settings

settings = get_settings()
celery_app = Celery("lynd", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/integration/test_referrals_api.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add src/api/ src/queue/ tests/integration/
git commit -m "feat: referral intake API with queue trigger"
```

---

## Task 6: Outreach Orchestrator (Retry Cadence)

**Files:**
- Create: `src/outreach/orchestrator.py`
- Modify: `src/queue/tasks.py`
- Test: `tests/unit/test_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_orchestrator.py
from unittest.mock import patch, MagicMock
from src.outreach.orchestrator import OutreachOrchestrator, OutreachCadence
from datetime import timedelta

def test_cadence_generates_correct_attempt_schedule():
    cadence = OutreachCadence.default()
    assert len(cadence.attempts) == 3
    assert cadence.attempts[0].delay_minutes == 0   # immediate
    assert cadence.attempts[1].delay_minutes == 30  # retry after 30 min
    assert cadence.attempts[2].delay_minutes == 240 # retry later same day

def test_orchestrator_schedules_all_attempts():
    mock_db = MagicMock()
    mock_referral = MagicMock(id=1, patient_id=1)

    with patch("src.outreach.orchestrator.make_outbound_call") as mock_call, \
         patch("src.outreach.orchestrator.send_sms_fallback") as mock_sms:
        orch = OutreachOrchestrator(db=mock_db)
        jobs = orch.create_outreach_jobs(mock_referral)
        assert len(jobs) == 3  # 3 voice attempts

def test_orchestrator_adds_sms_fallback_after_failed_calls():
    orch = OutreachOrchestrator(db=MagicMock())
    plan = orch.build_outreach_plan(referral_id=1)
    channels = [step["channel"] for step in plan]
    assert "sms" in channels
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_orchestrator.py -v
```

**Step 3: Implement orchestrator**

```python
# src/outreach/orchestrator.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from src.db.models import OutreachJob, OutreachStatus


@dataclass
class AttemptConfig:
    delay_minutes: int
    channel: str = "voice"


@dataclass
class OutreachCadence:
    attempts: List[AttemptConfig] = field(default_factory=list)

    @classmethod
    def default(cls) -> "OutreachCadence":
        return cls(attempts=[
            AttemptConfig(delay_minutes=0, channel="voice"),    # immediate call
            AttemptConfig(delay_minutes=30, channel="voice"),   # retry 30 min later
            AttemptConfig(delay_minutes=240, channel="voice"),  # retry 4 hours later
            AttemptConfig(delay_minutes=300, channel="sms"),    # SMS fallback
        ])


class OutreachOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.cadence = OutreachCadence.default()

    def build_outreach_plan(self, referral_id: int) -> List[dict]:
        plan = []
        for i, attempt in enumerate(self.cadence.attempts):
            plan.append({
                "referral_id": referral_id,
                "attempt_number": i + 1,
                "channel": attempt.channel,
                "delay_minutes": attempt.delay_minutes,
            })
        return plan

    def create_outreach_jobs(self, referral) -> List[OutreachJob]:
        plan = self.build_outreach_plan(referral.id)
        jobs = []
        now = datetime.utcnow()
        for step in plan:
            job = OutreachJob(
                referral_id=referral.id,
                attempt_number=step["attempt_number"],
                channel=step["channel"],
                status=OutreachStatus.QUEUED,
                scheduled_at=now + timedelta(minutes=step["delay_minutes"]),
            )
            self.db.add(job)
            jobs.append(job)
        self.db.commit()
        return jobs
```

**Step 4: Update queue tasks to use orchestrator**

```python
# src/queue/tasks.py (updated)
from src.queue.worker import celery_app
from src.db.session import SessionLocal
from src.db.models import Referral
from src.outreach.orchestrator import OutreachOrchestrator


@celery_app.task(name="queue_outreach")
def queue_outreach(referral_id: int):
    db = SessionLocal()
    try:
        referral = db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            return
        orch = OutreachOrchestrator(db=db)
        jobs = orch.create_outreach_jobs(referral)
        for job in jobs:
            execute_outreach_job.apply_async(
                args=[job.id],
                countdown=job.scheduled_at.timestamp() - __import__("time").time()
                if job.scheduled_at else 0
            )
    finally:
        db.close()


@celery_app.task(name="execute_outreach_job")
def execute_outreach_job(job_id: int):
    # Dispatches voice call or SMS — implemented in Tasks 8 & 19
    pass
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_orchestrator.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/outreach/ src/queue/
git commit -m "feat: outreach orchestrator with retry cadence"
```

---

## Task 7: Twilio Client — Outbound Call

**Files:**
- Create: `src/telephony/client.py`
- Test: `tests/unit/test_twilio_client.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_twilio_client.py
from unittest.mock import patch, MagicMock
from src.telephony.client import TwilioClient


def test_make_outbound_call_calls_twilio_api():
    with patch("src.telephony.client.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        mock_twilio.calls.create.return_value = MagicMock(sid="CA123")

        client = TwilioClient(account_sid="ACtest", auth_token="token", from_number="+15550000000")
        sid = client.make_outbound_call(
            to="+15551234567",
            webhook_url="https://lynd.com/webhooks/call/1/answer",
            status_callback_url="https://lynd.com/webhooks/call/1/status",
            machine_detection=True,
        )
        assert sid == "CA123"
        mock_twilio.calls.create.assert_called_once()


def test_make_outbound_call_passes_machine_detection():
    with patch("src.telephony.client.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        mock_twilio.calls.create.return_value = MagicMock(sid="CA456")

        client = TwilioClient(account_sid="ACtest", auth_token="token", from_number="+15550000000")
        client.make_outbound_call(
            to="+15551234567",
            webhook_url="https://lynd.com/webhooks/call/1/answer",
            status_callback_url="https://lynd.com/webhooks/call/1/status",
            machine_detection=True,
        )
        call_kwargs = mock_twilio.calls.create.call_args.kwargs
        assert call_kwargs.get("machine_detection") == "Enable"
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_twilio_client.py -v
```

**Step 3: Implement**

```python
# src/telephony/client.py
from twilio.rest import Client


class TwilioClient:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def make_outbound_call(
        self,
        to: str,
        webhook_url: str,
        status_callback_url: str,
        machine_detection: bool = True,
    ) -> str:
        """Initiates an outbound call and returns Twilio call SID."""
        kwargs = dict(
            to=to,
            from_=self.from_number,
            url=webhook_url,
            status_callback=status_callback_url,
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            record=True,
        )
        if machine_detection:
            kwargs["machine_detection"] = "Enable"
            kwargs["machine_detection_timeout"] = 30

        call = self.client.calls.create(**kwargs)
        return call.sid

    def send_sms(self, to: str, body: str) -> str:
        message = self.client.messages.create(to=to, from_=self.from_number, body=body)
        return message.sid
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_twilio_client.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/telephony/client.py tests/unit/test_twilio_client.py
git commit -m "feat: twilio client for outbound calls and sms"
```

---

## Task 8: Twilio Webhooks — Call Answer & Status

**Files:**
- Create: `src/api/routes/webhooks.py`
- Test: `tests/unit/test_webhooks.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_webhooks.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app

client = TestClient(app)


def test_answer_webhook_returns_twiml():
    with patch("src.api.routes.webhooks.get_db") as mock_db:
        mock_db.return_value = iter([MagicMock()])
        response = client.post(
            "/webhooks/call/1/answer",
            data={
                "CallSid": "CA123",
                "AnsweredBy": "human",
                "To": "+15551234567",
                "From": "+15550000000",
            }
        )
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Response>" in response.text


def test_answer_webhook_voicemail_plays_message():
    with patch("src.api.routes.webhooks.get_db") as mock_db:
        mock_db.return_value = iter([MagicMock()])
        response = client.post(
            "/webhooks/call/1/answer",
            data={
                "CallSid": "CA123",
                "AnsweredBy": "machine_start",
                "To": "+15551234567",
                "From": "+15550000000",
            }
        )
        assert response.status_code == 200
        # Voicemail response should say our message and hang up
        assert "Lynd Clinical" in response.text
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_webhooks.py -v
```

**Step 3: Implement webhooks route**

```python
# src/api/routes/webhooks.py
from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from src.api.dependencies import get_db
from src.config import get_settings

router = APIRouter()
settings = get_settings()

VOICEMAIL_MESSAGE = (
    "Hi, this is Lynd Clinical calling about a research opportunity "
    "your provider referred you for. We'll try again shortly. "
    "Thank you and have a great day."
)


@router.post("/call/{job_id}/answer")
async def handle_call_answer(
    job_id: int,
    CallSid: str = Form(...),
    AnsweredBy: str = Form(default="human"),
    To: str = Form(...),
    From_: str = Form(default="", alias="From"),
    db: Session = Depends(get_db),
):
    response = VoiceResponse()

    if AnsweredBy and AnsweredBy.startswith("machine"):
        # Voicemail — leave message with no PHI, then hang up
        response.say(VOICEMAIL_MESSAGE, voice="Polly.Joanna")
        response.hangup()
    else:
        # Human answered — connect to media stream for real-time conversation
        connect = Connect()
        stream = Stream(
            url=f"wss://{settings.app_base_url.replace('https://', '')}/webhooks/stream/{job_id}"
        )
        connect.append(stream)
        response.append(connect)

    return Response(content=str(response), media_type="application/xml")


@router.post("/call/{job_id}/status")
async def handle_call_status(
    job_id: int,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(default="0"),
    db: Session = Depends(get_db),
):
    """Records final call status — no PHI in this webhook."""
    from src.db.models import CallSession, OutreachJob, OutreachStatus, CallOutcome
    from datetime import datetime

    outcome_map = {
        "completed": CallOutcome.ANSWERED,
        "no-answer": CallOutcome.NO_ANSWER,
        "busy": CallOutcome.BUSY,
        "failed": CallOutcome.FAILED,
    }

    session = db.query(CallSession).filter(CallSession.twilio_call_sid == CallSid).first()
    if session:
        session.outcome = outcome_map.get(CallStatus, CallOutcome.FAILED)
        session.duration_seconds = int(CallDuration)
        session.ended_at = datetime.utcnow()
        db.commit()

    return Response(content="<Response/>", media_type="application/xml")
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_webhooks.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/api/routes/webhooks.py tests/unit/test_webhooks.py
git commit -m "feat: twilio webhook handlers for call answer and status"
```

---

## Task 9: Real-Time Audio — Deepgram STT

**Files:**
- Create: `src/audio/stt.py`
- Test: `tests/unit/test_stt.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_stt.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.audio.stt import DeepgramTranscriber


def test_transcriber_initializes_with_api_key():
    transcriber = DeepgramTranscriber(api_key="test_key")
    assert transcriber.api_key == "test_key"


@pytest.mark.asyncio
async def test_transcriber_returns_transcript_text():
    transcriber = DeepgramTranscriber(api_key="test_key")

    with patch.object(transcriber, "_connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = None
        # Simulate transcript callback
        result = transcriber._parse_transcript_response({
            "channel": {
                "alternatives": [{"transcript": "Hello my name is Jane"}]
            },
            "is_final": True,
        })
        assert result == "Hello my name is Jane"


def test_parse_transcript_returns_empty_for_non_final():
    transcriber = DeepgramTranscriber(api_key="test_key")
    result = transcriber._parse_transcript_response({
        "channel": {"alternatives": [{"transcript": "Hello"}]},
        "is_final": False,
    })
    assert result is None
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_stt.py -v
```

**Step 3: Implement**

```python
# src/audio/stt.py
import asyncio
import json
import base64
from typing import Callable, Optional
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions


class DeepgramTranscriber:
    """Wraps Deepgram streaming STT for real-time call transcription."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = DeepgramClient(api_key)
        self.connection = None
        self.on_transcript: Optional[Callable[[str], None]] = None

    def _parse_transcript_response(self, response: dict) -> Optional[str]:
        """Extracts final transcript text from Deepgram response dict."""
        if not response.get("is_final"):
            return None
        alternatives = response.get("channel", {}).get("alternatives", [])
        if not alternatives:
            return None
        text = alternatives[0].get("transcript", "").strip()
        return text if text else None

    async def start(self, on_transcript: Callable[[str], None]):
        """Opens a Deepgram streaming connection."""
        self.on_transcript = on_transcript
        self.connection = self.client.listen.asynclive.v("1")

        async def on_message(self_inner, result, **kwargs):
            text = self._parse_transcript_response(result.to_dict())
            if text and self.on_transcript:
                await self.on_transcript(text)

        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            encoding="mulaw",
            channels=1,
            sample_rate=8000,  # Twilio Media Streams default
            interim_results=False,
            endpointing=500,
        )
        await self.connection.start(options)

    async def send_audio(self, audio_bytes: bytes):
        """Sends raw audio bytes to Deepgram."""
        if self.connection:
            await self.connection.send(audio_bytes)

    async def finish(self):
        if self.connection:
            await self.connection.finish()
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_stt.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/audio/stt.py tests/unit/test_stt.py
git commit -m "feat: deepgram streaming STT integration"
```

---

## Task 10: ElevenLabs TTS

**Files:**
- Create: `src/audio/tts.py`
- Test: `tests/unit/test_tts.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_tts.py
from unittest.mock import patch, MagicMock
from src.audio.tts import ElevenLabsTTS


def test_tts_initializes():
    tts = ElevenLabsTTS(api_key="test_key", voice_id="voice_123")
    assert tts.voice_id == "voice_123"


def test_synthesize_returns_bytes():
    tts = ElevenLabsTTS(api_key="test_key", voice_id="voice_123")

    with patch("src.audio.tts.ElevenLabs") as MockEL:
        mock_client = MagicMock()
        MockEL.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter([b"audio_chunk_1", b"audio_chunk_2"])

        tts.client = mock_client
        audio = tts.synthesize("Hello, this is Lynd Clinical.")
        assert isinstance(audio, bytes)
        assert len(audio) > 0
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_tts.py -v
```

**Step 3: Implement**

```python
# src/audio/tts.py
import audioop
from elevenlabs import ElevenLabs
from elevenlabs.types import VoiceSettings


class ElevenLabsTTS:
    """Wraps ElevenLabs TTS, outputting mulaw audio for Twilio Media Streams."""

    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.client = ElevenLabs(api_key=api_key)

    def synthesize(self, text: str) -> bytes:
        """Returns mulaw-encoded audio bytes suitable for Twilio."""
        audio_chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
            ),
            output_format="pcm_16000",  # 16kHz PCM, then downsample to 8kHz mulaw
        )
        pcm_data = b"".join(audio_chunks)
        # Downsample 16kHz -> 8kHz, then convert linear16 -> mulaw for Twilio
        downsampled, _ = audioop.ratecv(pcm_data, 2, 1, 16000, 8000, None)
        mulaw_data = audioop.lin2ulaw(downsampled, 2)
        return mulaw_data
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_tts.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/audio/tts.py tests/unit/test_tts.py
git commit -m "feat: elevenlabs TTS with mulaw output for twilio"
```

---

## Task 11: Conversation State Machine Core

**Files:**
- Create: `src/conversation/state_machine.py`
- Test: `tests/unit/test_state_machine.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_state_machine.py
from src.conversation.state_machine import ConversationMachine, ConversationContext
from src.db.models import ConversationState


def test_machine_starts_in_identity_verification():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    assert machine.current_state == ConversationState.IDENTITY_VERIFICATION


def test_machine_transitions_to_introduction_after_identity_verified():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    machine.transition(ConversationState.INTRODUCTION)
    assert machine.current_state == ConversationState.INTRODUCTION


def test_machine_cannot_skip_identity_verification():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    import pytest
    with pytest.raises(ValueError, match="Invalid transition"):
        machine.transition(ConversationState.PRE_SCREEN)


def test_machine_can_always_escalate():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    machine = ConversationMachine(context=ctx)
    machine.transition(ConversationState.ESCALATION)
    assert machine.current_state == ConversationState.ESCALATION


def test_context_stores_pre_screen_responses():
    ctx = ConversationContext(patient_name="Jane", study_id="STUDY-001")
    ctx.record_response("age_eligible", "yes", "Yes, I am 45 years old")
    assert ctx.pre_screen_responses["age_eligible"]["value"] == "yes"
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_state_machine.py -v
```

**Step 3: Implement**

```python
# src/conversation/state_machine.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from src.db.models import ConversationState

# Valid state transitions
TRANSITIONS = {
    ConversationState.IDENTITY_VERIFICATION: {
        ConversationState.INTRODUCTION,
        ConversationState.ESCALATION,
    },
    ConversationState.INTRODUCTION: {
        ConversationState.PRE_SCREEN,
        ConversationState.ESCALATION,
    },
    ConversationState.PRE_SCREEN: {
        ConversationState.SCHEDULING,
        ConversationState.ESCALATION,
    },
    ConversationState.SCHEDULING: {
        ConversationState.COMPLETED,
        ConversationState.ESCALATION,
    },
    ConversationState.ESCALATION: {
        ConversationState.COMPLETED,
    },
    ConversationState.COMPLETED: set(),
}

# From any state, escalation is always allowed
ALWAYS_ALLOWED = {ConversationState.ESCALATION, ConversationState.COMPLETED}


@dataclass
class ConversationContext:
    patient_name: str
    study_id: str
    identity_verified: bool = False
    interest_level: Optional[str] = None  # interested, not_interested, undecided
    scheduling_outcome: Optional[str] = None  # scheduled, callback_requested, declined
    pre_screen_responses: dict = field(default_factory=dict)
    transcript_segments: list = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)

    def record_response(self, question_key: str, value: str, raw_text: str):
        self.pre_screen_responses[question_key] = {
            "value": value,
            "raw_text": raw_text,
            "captured_at": datetime.utcnow().isoformat(),
        }

    def append_transcript(self, speaker: str, text: str):
        self.transcript_segments.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })


class ConversationMachine:
    def __init__(self, context: ConversationContext):
        self.context = context
        self.current_state = ConversationState.IDENTITY_VERIFICATION
        self.history: list[ConversationState] = [self.current_state]

    def transition(self, new_state: ConversationState):
        allowed = TRANSITIONS.get(self.current_state, set()) | ALWAYS_ALLOWED
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.current_state} -> {new_state}. "
                f"Allowed: {allowed}"
            )
        self.current_state = new_state
        self.history.append(new_state)

    def can_transition(self, new_state: ConversationState) -> bool:
        allowed = TRANSITIONS.get(self.current_state, set()) | ALWAYS_ALLOWED
        return new_state in allowed
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_state_machine.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/conversation/state_machine.py tests/unit/test_state_machine.py
git commit -m "feat: conversation state machine with validated transitions"
```

---

## Task 12: Claude LLM Client & Intent Detection

**Files:**
- Create: `src/llm/client.py`
- Create: `src/llm/intent.py`
- Test: `tests/unit/test_intent.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_intent.py
from unittest.mock import patch, MagicMock
from src.llm.intent import IntentDetector, Intent


def test_intent_detector_classifies_escalation_request():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock_claude:
        mock_claude.return_value = "ESCALATE"
        intent = detector.detect("Can I speak to a real person please?", state="pre_screen")
        assert intent == Intent.ESCALATE


def test_intent_detector_classifies_confirmation():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock_claude:
        mock_claude.return_value = "CONFIRM"
        intent = detector.detect("Yes, that's right", state="identity_verification")
        assert intent == Intent.CONFIRM


def test_intent_detector_classifies_schedule_request():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock_claude:
        mock_claude.return_value = "SCHEDULE"
        intent = detector.detect("I'd like to schedule a call for tomorrow", state="scheduling")
        assert intent == Intent.SCHEDULE


def test_known_intents_are_defined():
    assert Intent.ESCALATE
    assert Intent.CONFIRM
    assert Intent.DENY
    assert Intent.SCHEDULE
    assert Intent.CALLBACK
    assert Intent.UNCLEAR
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_intent.py -v
```

**Step 3: Implement LLM client**

```python
# src/llm/client.py
import anthropic


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 100) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text.strip()
```

**Step 4: Implement intent detector**

```python
# src/llm/intent.py
import enum
from src.llm.client import ClaudeClient

INTENT_SYSTEM_PROMPT = """You are classifying patient intent in a clinical trial recruitment call.
Based on what the patient said and the current conversation state, return EXACTLY ONE of:
CONFIRM - patient is agreeing, confirming, or saying yes
DENY - patient is disagreeing, saying no, or declining
ESCALATE - patient wants to speak to a human or has a medical question
SCHEDULE - patient wants to book a specific appointment time
CALLBACK - patient wants to be called back later
UNCLEAR - patient's intent cannot be determined

Return only the single word. No explanation."""


class Intent(str, enum.Enum):
    CONFIRM = "CONFIRM"
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    SCHEDULE = "SCHEDULE"
    CALLBACK = "CALLBACK"
    UNCLEAR = "UNCLEAR"


class IntentDetector:
    def __init__(self, api_key: str):
        self.claude = ClaudeClient(api_key=api_key)

    def _call_claude(self, patient_text: str, state: str) -> str:
        user_msg = f"Conversation state: {state}\nPatient said: \"{patient_text}\""
        return self.claude.complete(
            system=INTENT_SYSTEM_PROMPT,
            user=user_msg,
            max_tokens=10,
        )

    def detect(self, patient_text: str, state: str) -> Intent:
        raw = self._call_claude(patient_text, state).strip().upper()
        try:
            return Intent(raw)
        except ValueError:
            return Intent.UNCLEAR
```

**Step 5: Run tests**

```bash
pytest tests/unit/test_intent.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/llm/ tests/unit/test_intent.py
git commit -m "feat: claude intent detection for conversation routing"
```

---

## Task 13: Conversation States — Identity Verification

**Files:**
- Create: `src/conversation/states/identity.py`
- Test: `tests/unit/test_identity_state.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_identity_state.py
from unittest.mock import MagicMock, patch
from src.conversation.states.identity import IdentityVerificationState
from src.conversation.state_machine import ConversationContext, ConversationMachine
from src.llm.intent import Intent
from src.db.models import ConversationState


def make_context():
    return ConversationContext(patient_name="Jane Doe", study_id="STUDY-001")


def test_identity_state_returns_greeting_prompt():
    state = IdentityVerificationState()
    ctx = make_context()
    prompt = state.get_opening_prompt(ctx)
    assert "Jane" in prompt
    assert "date of birth" in prompt.lower()


def test_identity_state_verifies_correct_dob():
    state = IdentityVerificationState()
    ctx = make_context()
    # Patient provides correct DOB
    result = state.verify_dob(patient_said="January 15, 1980", actual_dob="1980-01-15")
    assert result is True


def test_identity_state_rejects_wrong_dob():
    state = IdentityVerificationState()
    ctx = make_context()
    result = state.verify_dob(patient_said="March 5, 1985", actual_dob="1980-01-15")
    assert result is False


def test_identity_state_returns_next_state_on_success():
    state = IdentityVerificationState()
    ctx = make_context()
    machine = ConversationMachine(context=ctx)

    with patch.object(state, "verify_dob", return_value=True):
        next_state, response = state.handle_response(
            patient_text="January 15, 1980",
            context=ctx,
            actual_dob="1980-01-15",
        )
    assert next_state == ConversationState.INTRODUCTION
    assert ctx.identity_verified is True


def test_identity_state_allows_one_retry_on_failure():
    state = IdentityVerificationState()
    ctx = make_context()

    with patch.object(state, "verify_dob", return_value=False):
        next_state, response = state.handle_response(
            patient_text="wrong date",
            context=ctx,
            actual_dob="1980-01-15",
            attempt=1,
        )
    assert next_state == ConversationState.IDENTITY_VERIFICATION
    assert "try again" in response.lower()


def test_identity_state_escalates_after_two_failures():
    state = IdentityVerificationState()
    ctx = make_context()

    with patch.object(state, "verify_dob", return_value=False):
        next_state, response = state.handle_response(
            patient_text="wrong date",
            context=ctx,
            actual_dob="1980-01-15",
            attempt=2,
        )
    assert next_state == ConversationState.ESCALATION
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_identity_state.py -v
```

**Step 3: Implement**

```python
# src/conversation/states/identity.py
from typing import Tuple
from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext


DOB_PARSE_SYSTEM = """Extract a date of birth from natural speech and return it in YYYY-MM-DD format.
Examples: 'January 15th 1980' -> '1980-01-15', 'the fifth of March, 85' -> '1985-03-05'
Return ONLY the date string. If you cannot parse a date, return 'UNKNOWN'."""


class IdentityVerificationState:
    def get_opening_prompt(self, context: ConversationContext) -> str:
        first_name = context.patient_name.split()[0]
        return (
            f"Hi, may I please speak with {first_name}? "
            f"Great — to make sure I'm speaking with the right person, "
            f"could you please confirm your date of birth?"
        )

    def verify_dob(self, patient_said: str, actual_dob: str) -> bool:
        """Uses Claude to parse the spoken DOB and compare to record."""
        from src.llm.client import ClaudeClient
        from src.config import get_settings
        settings = get_settings()
        claude = ClaudeClient(api_key=settings.anthropic_api_key)
        parsed = claude.complete(
            system=DOB_PARSE_SYSTEM,
            user=patient_said,
            max_tokens=20,
        ).strip()
        return parsed == actual_dob

    def handle_response(
        self,
        patient_text: str,
        context: ConversationContext,
        actual_dob: str,
        attempt: int = 1,
    ) -> Tuple[ConversationState, str]:
        if self.verify_dob(patient_said=patient_text, actual_dob=actual_dob):
            context.identity_verified = True
            return (
                ConversationState.INTRODUCTION,
                "Thank you for confirming. I'm calling from Lynd Clinical "
                "about a research opportunity your provider referred you for. "
                "Do you have a few minutes to hear about it?",
            )
        elif attempt < 2:
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "I'm sorry, I didn't quite catch that. Could you try again "
                "with your date of birth?",
            )
        else:
            return (
                ConversationState.ESCALATION,
                "I'm having trouble verifying your information. "
                "Let me connect you with a member of our study team who can help.",
            )
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_identity_state.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/conversation/states/identity.py tests/unit/test_identity_state.py
git commit -m "feat: identity verification state with DOB confirmation"
```

---

## Task 14: Conversation States — Introduction, Pre-Screen, Scheduling, Escalation

**Files:**
- Create: `src/conversation/states/introduction.py`
- Create: `src/conversation/states/prescreen.py`
- Create: `src/conversation/states/scheduling.py`
- Create: `src/conversation/states/escalation.py`
- Test: `tests/unit/test_conversation_states.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_conversation_states.py
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


def test_introduction_advances_on_interest():
    state = IntroductionState()
    ctx = make_context()
    with patch("src.conversation.states.introduction.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CONFIRM
        next_state, _ = state.handle_response("Yes I'm interested", ctx)
    assert next_state == ConversationState.PRE_SCREEN


def test_introduction_escalates_on_not_interested():
    state = IntroductionState()
    ctx = make_context()
    with patch("src.conversation.states.introduction.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.DENY
        next_state, response = state.handle_response("No thank you", ctx)
    assert next_state == ConversationState.COMPLETED
    assert ctx.interest_level == "not_interested"


def test_prescreen_captures_structured_response():
    state = PreScreenState(questions=[
        {"key": "age_eligible", "text": "Are you between 18 and 70 years old?"},
    ])
    ctx = make_context()
    with patch("src.conversation.states.prescreen.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.CONFIRM
        next_state, _, responses = state.handle_response("Yes I am 45", ctx, question_index=0)
    assert ctx.pre_screen_responses["age_eligible"]["value"] == "yes"


def test_scheduling_captures_calendly_link_on_schedule():
    state = SchedulingState(calendly_event_url="https://calendly.com/lynd/screening")
    ctx = make_context()
    with patch("src.conversation.states.scheduling.IntentDetector") as MockDetector:
        MockDetector.return_value.detect.return_value = Intent.SCHEDULE
        next_state, response = state.handle_response("I'd like to schedule for tomorrow", ctx)
    assert next_state == ConversationState.COMPLETED
    assert ctx.scheduling_outcome == "scheduled"


def test_escalation_state_returns_handoff_message():
    state = EscalationState()
    ctx = make_context()
    message = state.get_handoff_message()
    assert "study team" in message.lower() or "coordinator" in message.lower()
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_conversation_states.py -v
```

**Step 3: Implement all four states**

```python
# src/conversation/states/introduction.py
from typing import Tuple
from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent
from src.config import get_settings

STUDY_OVERVIEW = (
    "We're conducting a clinical research study and your provider thought you might be a good fit. "
    "The study involves {study_details}. Participation is entirely voluntary and confidential. "
    "Would you like to hear more and answer a few quick questions to see if you qualify?"
)


class IntroductionState:
    def get_opening_prompt(self, context: ConversationContext) -> str:
        return (
            "I'm calling from Lynd Clinical about a research opportunity "
            "your provider referred you for. We're conducting a clinical study "
            "and your doctor thought you might qualify. "
            "Do you have a couple of minutes to learn more?"
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext
    ) -> Tuple[ConversationState, str]:
        settings = get_settings()
        detector = IntentDetector(api_key=settings.anthropic_api_key)
        intent = detector.detect(patient_text, state="introduction")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "Of course — let me connect you with a member of our study team.",
            )
        elif intent == Intent.DENY:
            context.interest_level = "not_interested"
            return (
                ConversationState.COMPLETED,
                "No problem at all. Thank you for your time, and have a great day.",
            )
        else:
            context.interest_level = "interested"
            return (
                ConversationState.PRE_SCREEN,
                "Great, thank you! I just have a few quick questions to see if you may qualify. "
                "This should only take about two minutes.",
            )
```

```python
# src/conversation/states/prescreen.py
from typing import Tuple, List, Optional
from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent
from src.config import get_settings


class PreScreenState:
    def __init__(self, questions: List[dict]):
        """questions: list of {key: str, text: str}"""
        self.questions = questions

    def get_current_question(self, index: int) -> Optional[dict]:
        if index < len(self.questions):
            return self.questions[index]
        return None

    def handle_response(
        self,
        patient_text: str,
        context: ConversationContext,
        question_index: int,
    ) -> Tuple[ConversationState, str, dict]:
        settings = get_settings()
        detector = IntentDetector(api_key=settings.anthropic_api_key)
        intent = detector.detect(patient_text, state="pre_screen")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "I can connect you with a member of our study team to answer that.",
                {},
            )

        question = self.questions[question_index]
        value = "yes" if intent == Intent.CONFIRM else "no" if intent == Intent.DENY else "unclear"
        context.record_response(
            question_key=question["key"],
            value=value,
            raw_text=patient_text,
        )

        next_index = question_index + 1
        if next_index < len(self.questions):
            next_question = self.questions[next_index]
            return (
                ConversationState.PRE_SCREEN,
                next_question["text"],
                {"next_question_index": next_index},
            )
        else:
            return (
                ConversationState.SCHEDULING,
                "Thank you for answering those questions. Based on what you've told me, "
                "the next step would be a brief screening call with our study coordinator. "
                "Would you like to schedule that now?",
                {},
            )
```

```python
# src/conversation/states/scheduling.py
from typing import Tuple
from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent
from src.config import get_settings


class SchedulingState:
    def __init__(self, calendly_event_url: str):
        self.calendly_event_url = calendly_event_url

    def get_opening_prompt(self) -> str:
        return (
            "Would you like to schedule a brief screening call with our coordinator? "
            "I can also send you a link by text message so you can pick a time that works best for you."
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext
    ) -> Tuple[ConversationState, str]:
        settings = get_settings()
        detector = IntentDetector(api_key=settings.anthropic_api_key)
        intent = detector.detect(patient_text, state="scheduling")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "I'll connect you with our study team right away.",
            )
        elif intent in (Intent.SCHEDULE, Intent.CONFIRM):
            context.scheduling_outcome = "scheduled"
            return (
                ConversationState.COMPLETED,
                f"Wonderful! I'll send you a text message with a scheduling link so you can pick "
                f"the time that works best for you. The link will be for {self.calendly_event_url}. "
                f"Thank you so much for your interest in the study!",
            )
        elif intent == Intent.CALLBACK:
            context.scheduling_outcome = "callback_requested"
            return (
                ConversationState.COMPLETED,
                "Of course — I'll make a note that you'd like us to follow up. "
                "Our coordinator will reach out to find a good time. Thank you!",
            )
        else:
            context.scheduling_outcome = "declined"
            return (
                ConversationState.COMPLETED,
                "No problem at all. If you change your mind, our study team would be "
                "happy to hear from you. Thank you for your time today!",
            )
```

```python
# src/conversation/states/escalation.py
from src.conversation.state_machine import ConversationContext


class EscalationState:
    def get_handoff_message(self) -> str:
        return (
            "I'm going to connect you with a member of our study team "
            "who can answer your questions directly. Please hold for just a moment."
        )

    def get_voicemail_handoff_message(self) -> str:
        return (
            "Our study coordinator will follow up with you shortly. "
            "Thank you for your interest."
        )
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_conversation_states.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/conversation/states/ tests/unit/test_conversation_states.py
git commit -m "feat: all conversation states - introduction, pre-screen, scheduling, escalation"
```

---

## Task 15: RAG Knowledge Base (IRB Script Retrieval)

**Files:**
- Create: `src/rag/knowledge_base.py`
- Create: `src/rag/retrieval.py`
- Create: `scripts/ingest_irb_script.py`
- Test: `tests/unit/test_rag.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_rag.py
from unittest.mock import patch, MagicMock
from src.rag.knowledge_base import KnowledgeBase
from src.rag.retrieval import IRBRetriever


def test_knowledge_base_ingests_content():
    kb = KnowledgeBase(db_session=MagicMock())
    with patch.object(kb, "_embed") as mock_embed, \
         patch.object(kb, "_store") as mock_store:
        mock_embed.return_value = [0.1] * 1536
        kb.add_entry(
            key="age_requirement",
            content="Participants must be between 18 and 70 years old.",
            tags=["eligibility", "age"],
        )
        mock_store.assert_called_once()


def test_retriever_returns_approved_content():
    retriever = IRBRetriever(db_session=MagicMock())
    with patch.object(retriever, "_search") as mock_search:
        mock_search.return_value = [
            {"content": "Participants must be 18-70.", "score": 0.95}
        ]
        results = retriever.search("what is the age requirement?", top_k=1)
        assert len(results) == 1
        assert "18-70" in results[0]["content"]


def test_retriever_returns_empty_for_no_match():
    retriever = IRBRetriever(db_session=MagicMock())
    with patch.object(retriever, "_search") as mock_search:
        mock_search.return_value = []
        results = retriever.search("unrelated query", top_k=1)
        assert results == []
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_rag.py -v
```

**Step 3: Add pgvector to DB models**

Add to `src/db/models.py`:
```python
from pgvector.sqlalchemy import Vector

class IRBKnowledgeEntry(Base):
    __tablename__ = "irb_knowledge"
    id = Column(Integer, primary_key=True)
    key = Column(String(200), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=[])
    embedding = Column(Vector(1536))  # OpenAI/Claude embedding dimension
    study_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 4: Generate migration for new table**

```bash
DATABASE_URL=postgresql://lynd:lynd_dev@localhost:5432/lynd alembic revision --autogenerate -m "add irb knowledge table"
DATABASE_URL=postgresql://lynd:lynd_dev@localhost:5432/lynd alembic upgrade head
```

**Step 5: Implement knowledge base and retriever**

```python
# src/rag/knowledge_base.py
from typing import List
from sqlalchemy.orm import Session
from src.db.models import IRBKnowledgeEntry
import anthropic


class KnowledgeBase:
    def __init__(self, db_session: Session, api_key: str = ""):
        self.db = db_session
        self.api_key = api_key

    def _embed(self, text: str) -> List[float]:
        # Use Voyage AI or simple sentence transformers for embeddings
        # For V1, use a simple approach via Anthropic or a dedicated embedding service
        # Placeholder: returns zero vector — replace with real embedding call
        raise NotImplementedError("Implement with your embedding provider")

    def _store(self, entry: IRBKnowledgeEntry):
        self.db.add(entry)
        self.db.commit()

    def add_entry(self, key: str, content: str, tags: List[str], study_id: str = ""):
        embedding = self._embed(content)
        entry = IRBKnowledgeEntry(
            key=key,
            content=content,
            tags=tags,
            embedding=embedding,
            study_id=study_id,
        )
        self._store(entry)
```

```python
# src/rag/retrieval.py
from typing import List, dict
from sqlalchemy.orm import Session
from sqlalchemy import text


class IRBRetriever:
    def __init__(self, db_session: Session, api_key: str = ""):
        self.db = db_session
        self.api_key = api_key

    def _embed(self, text_input: str) -> List[float]:
        raise NotImplementedError("Implement with your embedding provider")

    def _search(self, query_embedding: List[float], top_k: int) -> List[dict]:
        result = self.db.execute(
            text("""
                SELECT key, content, tags,
                       1 - (embedding <=> cast(:embedding AS vector)) as score
                FROM irb_knowledge
                ORDER BY embedding <=> cast(:embedding AS vector)
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k},
        )
        return [{"content": row.content, "score": row.score} for row in result]

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        try:
            embedding = self._embed(query)
            return self._search(embedding, top_k)
        except Exception:
            return []
```

```python
# scripts/ingest_irb_script.py
"""
Usage: python scripts/ingest_irb_script.py --file path/to/irb_script.txt --study-id STUDY-001

This script converts an IRB-approved script document into knowledge base entries.
Run this before deploying for each new study.
"""
import argparse
import sys
sys.path.insert(0, ".")

from src.db.session import SessionLocal
from src.rag.knowledge_base import KnowledgeBase


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--study-id", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    kb = KnowledgeBase(db_session=db)

    with open(args.file) as f:
        content = f.read()

    # Simple paragraph-based segmentation for V1
    # Improve this with better chunking for production
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        kb.add_entry(
            key=f"{args.study_id}-segment-{i}",
            content=para,
            tags=["irb_approved", args.study_id],
            study_id=args.study_id,
        )
        print(f"Ingested segment {i+1}/{len(paragraphs)}")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
```

**NOTE:** For embedding provider, use [Voyage AI](https://www.voyageai.com/) (1024-dim) or OpenAI `text-embedding-3-small` (1536-dim). Add the appropriate SDK and update `_embed()` in both files. Voyage AI is cheaper for this use case.

**Step 6: Run tests**

```bash
pytest tests/unit/test_rag.py -v
```

Expected: PASS (tests mock the embed/search methods)

**Step 7: Commit**

```bash
git add src/rag/ src/db/models.py scripts/ tests/unit/test_rag.py
git commit -m "feat: RAG knowledge base for IRB script retrieval"
```

---

## Task 16: WebSocket Call Handler (Tie It All Together)

**Files:**
- Create: `src/telephony/call_handler.py`
- Modify: `src/api/routes/webhooks.py` (add WebSocket endpoint)
- Test: `tests/unit/test_call_handler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_call_handler.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.telephony.call_handler import CallHandler
from src.conversation.state_machine import ConversationContext, ConversationMachine
from src.db.models import ConversationState


@pytest.mark.asyncio
async def test_call_handler_initializes_state_machine():
    handler = CallHandler(
        context=ConversationContext(patient_name="Jane Doe", study_id="STUDY-001"),
        patient_dob="1980-01-15",
        job_id=1,
        db=MagicMock(),
    )
    assert handler.machine.current_state == ConversationState.IDENTITY_VERIFICATION


@pytest.mark.asyncio
async def test_call_handler_sends_opening_prompt():
    handler = CallHandler(
        context=ConversationContext(patient_name="Jane Doe", study_id="STUDY-001"),
        patient_dob="1980-01-15",
        job_id=1,
        db=MagicMock(),
    )
    with patch.object(handler, "speak", new_callable=AsyncMock) as mock_speak:
        await handler.on_call_start()
        mock_speak.assert_called_once()
        args = mock_speak.call_args[0][0]
        assert "Jane" in args


@pytest.mark.asyncio
async def test_call_handler_routes_transcript_to_current_state():
    handler = CallHandler(
        context=ConversationContext(patient_name="Jane Doe", study_id="STUDY-001"),
        patient_dob="1980-01-15",
        job_id=1,
        db=MagicMock(),
    )
    with patch.object(handler, "speak", new_callable=AsyncMock), \
         patch.object(handler.identity_state, "handle_response") as mock_handle:
        mock_handle.return_value = (ConversationState.INTRODUCTION, "Thank you")
        await handler.on_transcript("January 15, 1980")
        mock_handle.assert_called_once()
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_call_handler.py -v
```

**Step 3: Implement call handler**

```python
# src/telephony/call_handler.py
import asyncio
import base64
import json
from typing import Optional
from sqlalchemy.orm import Session

from src.conversation.state_machine import ConversationContext, ConversationMachine
from src.conversation.states.identity import IdentityVerificationState
from src.conversation.states.introduction import IntroductionState
from src.conversation.states.prescreen import PreScreenState
from src.conversation.states.scheduling import SchedulingState
from src.conversation.states.escalation import EscalationState
from src.audio.stt import DeepgramTranscriber
from src.audio.tts import ElevenLabsTTS
from src.db.models import ConversationState, CallSession
from src.config import get_settings

# Default pre-screen questions — override per study
DEFAULT_PRESCREEN_QUESTIONS = [
    {"key": "age_eligible", "text": "Are you between 18 and 70 years old?"},
    {"key": "diagnosis_confirmed", "text": "Have you been diagnosed with the condition your doctor referred you about?"},
    {"key": "no_conflicting_treatment", "text": "Are you currently free from any treatments that might interfere with a clinical study?"},
]


class CallHandler:
    """Orchestrates a real-time voice conversation for one call session."""

    def __init__(
        self,
        context: ConversationContext,
        patient_dob: str,
        job_id: int,
        db: Session,
        websocket=None,
    ):
        settings = get_settings()
        self.context = context
        self.patient_dob = patient_dob
        self.job_id = job_id
        self.db = db
        self.websocket = websocket
        self.machine = ConversationMachine(context=context)
        self.stt = DeepgramTranscriber(api_key=settings.deepgram_api_key)
        self.tts = ElevenLabsTTS(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
        )
        self.identity_state = IdentityVerificationState()
        self.introduction_state = IntroductionState()
        self.prescreen_state = PreScreenState(questions=DEFAULT_PRESCREEN_QUESTIONS)
        self.scheduling_state = SchedulingState(
            calendly_event_url=settings.calendly_event_url
        )
        self.escalation_state = EscalationState()
        self._prescreen_question_index = 0
        self._identity_attempt = 1

    async def speak(self, text: str):
        """Synthesize text and stream audio back to Twilio."""
        self.context.append_transcript("agent", text)
        audio = self.tts.synthesize(text)
        if self.websocket:
            await self._send_audio_to_twilio(audio)

    async def _send_audio_to_twilio(self, audio_bytes: bytes):
        """Send mulaw audio chunks to Twilio Media Streams."""
        chunk_size = 160  # 20ms at 8kHz mulaw
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            payload = {
                "event": "media",
                "media": {
                    "payload": base64.b64encode(chunk).decode("utf-8")
                }
            }
            await self.websocket.send_text(json.dumps(payload))

    async def on_call_start(self):
        prompt = self.identity_state.get_opening_prompt(self.context)
        await self.speak(prompt)

    async def on_transcript(self, patient_text: str):
        self.context.append_transcript("patient", patient_text)
        state = self.machine.current_state

        if state == ConversationState.IDENTITY_VERIFICATION:
            next_state, response = self.identity_state.handle_response(
                patient_text=patient_text,
                context=self.context,
                actual_dob=self.patient_dob,
                attempt=self._identity_attempt,
            )
            self._identity_attempt += 1
            self.machine.transition(next_state)
            await self.speak(response)

        elif state == ConversationState.INTRODUCTION:
            next_state, response = self.introduction_state.handle_response(
                patient_text=patient_text,
                context=self.context,
            )
            self.machine.transition(next_state)
            await self.speak(response)

        elif state == ConversationState.PRE_SCREEN:
            next_state, response, extras = self.prescreen_state.handle_response(
                patient_text=patient_text,
                context=self.context,
                question_index=self._prescreen_question_index,
            )
            self._prescreen_question_index = extras.get(
                "next_question_index", self._prescreen_question_index
            )
            self.machine.transition(next_state)
            await self.speak(response)

        elif state == ConversationState.SCHEDULING:
            next_state, response = self.scheduling_state.handle_response(
                patient_text=patient_text,
                context=self.context,
            )
            self.machine.transition(next_state)
            await self.speak(response)

    async def run_websocket_session(self):
        """Main loop — receive Twilio Media Streams messages and process audio."""
        await self.stt.start(on_transcript=self.on_transcript)
        await self.on_call_start()

        try:
            while True:
                data = await self.websocket.receive_text()
                msg = json.loads(data)

                if msg["event"] == "media":
                    audio_bytes = base64.b64decode(msg["media"]["payload"])
                    await self.stt.send_audio(audio_bytes)
                elif msg["event"] == "stop":
                    break
        finally:
            await self.stt.finish()
            self._save_session()

    def _save_session(self):
        session = self.db.query(CallSession).filter(
            CallSession.outreach_job_id == self.job_id
        ).first()
        if session:
            session.final_state = self.machine.current_state
            session.transcript = json.dumps(self.context.transcript_segments)
            self.db.commit()
```

**Step 4: Add WebSocket endpoint to webhooks.py**

Add to `src/api/routes/webhooks.py`:
```python
from fastapi import WebSocket
from src.telephony.call_handler import CallHandler
from src.db.models import OutreachJob, Patient, Referral, CallSession

@router.websocket("/stream/{job_id}")
async def handle_media_stream(job_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()

    job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
    if not job:
        await websocket.close()
        return

    referral = db.query(Referral).filter(Referral.id == job.referral_id).first()
    patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()

    context = ConversationContext(
        patient_name=f"{patient.first_name} {patient.last_name}",
        study_id=referral.study_id,
    )
    handler = CallHandler(
        context=context,
        patient_dob=patient.date_of_birth,
        job_id=job_id,
        db=db,
        websocket=websocket,
    )
    await handler.run_websocket_session()
```

**Step 5: Run tests**

```bash
pytest tests/unit/test_call_handler.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/telephony/call_handler.py src/api/routes/webhooks.py tests/unit/test_call_handler.py
git commit -m "feat: websocket call handler ties STT, TTS, and state machine together"
```

---

## Task 17: SMS Fallback

**Files:**
- Create: `src/telephony/sms.py`
- Modify: `src/queue/tasks.py`
- Test: `tests/unit/test_sms.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_sms.py
from unittest.mock import patch, MagicMock
from src.telephony.sms import SMSOutreach


def test_sms_sends_initial_outreach_message():
    sms = SMSOutreach(twilio_client=MagicMock(), calendly_url="https://calendly.com/lynd/screening")
    sms.client.send_sms = MagicMock(return_value="SM123")
    sid = sms.send_initial_outreach(
        to="+15551234567",
        patient_first_name="Jane",
        study_id="STUDY-001",
    )
    assert sid == "SM123"
    call_args = sms.client.send_sms.call_args
    body = call_args.kwargs.get("body") or call_args.args[1]
    assert "Jane" in body
    assert "calendly.com" in body


def test_sms_message_contains_no_phi():
    sms = SMSOutreach(twilio_client=MagicMock(), calendly_url="https://calendly.com/lynd/screening")
    sms.client.send_sms = MagicMock(return_value="SM123")
    sms.send_initial_outreach(
        to="+15551234567",
        patient_first_name="Jane",
        study_id="STUDY-001",
    )
    call_args = sms.client.send_sms.call_args
    body = call_args.kwargs.get("body") or call_args.args[1]
    # Must not include DOB or other PHI
    assert "date of birth" not in body.lower()
    assert "diagnosis" not in body.lower()
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_sms.py -v
```

**Step 3: Implement**

```python
# src/telephony/sms.py
from src.telephony.client import TwilioClient


SMS_INITIAL_OUTREACH = (
    "Hi {first_name}, this is Lynd Clinical. Your provider referred you for a research "
    "opportunity that may be a good fit for you. To learn more and see if you qualify, "
    "you can schedule a brief call here: {calendly_url} "
    "Reply STOP to opt out."
)


class SMSOutreach:
    def __init__(self, twilio_client: TwilioClient, calendly_url: str):
        self.client = twilio_client
        self.calendly_url = calendly_url

    def send_initial_outreach(self, to: str, patient_first_name: str, study_id: str) -> str:
        body = SMS_INITIAL_OUTREACH.format(
            first_name=patient_first_name,
            calendly_url=self.calendly_url,
        )
        return self.client.send_sms(to=to, body=body)

    def send_scheduling_link(self, to: str, patient_first_name: str) -> str:
        body = (
            f"Hi {patient_first_name}, here is your scheduling link for your "
            f"Lynd Clinical screening call: {self.calendly_url}"
        )
        return self.client.send_sms(to=to, body=body)
```

**Step 4: Wire SMS into execute_outreach_job task**

Update `src/queue/tasks.py`:
```python
@celery_app.task(name="execute_outreach_job")
def execute_outreach_job(job_id: int):
    from src.db.models import OutreachJob, OutreachStatus, Referral, Patient, CallSession
    from src.telephony.client import TwilioClient
    from src.telephony.sms import SMSOutreach
    from src.config import get_settings
    from datetime import datetime

    db = SessionLocal()
    settings = get_settings()
    try:
        job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
        if not job or job.status != OutreachStatus.QUEUED:
            return

        job.status = OutreachStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        db.commit()

        referral = db.query(Referral).filter(Referral.id == job.referral_id).first()
        patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()
        twilio = TwilioClient(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_phone_number,
        )

        if job.channel == "voice":
            call_sid = twilio.make_outbound_call(
                to=patient.phone,
                webhook_url=f"{settings.app_base_url}/webhooks/call/{job_id}/answer",
                status_callback_url=f"{settings.app_base_url}/webhooks/call/{job_id}/status",
                machine_detection=True,
            )
            call_session = CallSession(
                outreach_job_id=job_id,
                twilio_call_sid=call_sid,
            )
            db.add(call_session)
        elif job.channel == "sms":
            sms = SMSOutreach(twilio_client=twilio, calendly_url=settings.calendly_event_url)
            sms.send_initial_outreach(
                to=patient.phone,
                patient_first_name=patient.first_name,
                study_id=referral.study_id,
            )

        job.status = OutreachStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        job.status = OutreachStatus.FAILED
        db.commit()
        raise
    finally:
        db.close()
```

**Step 5: Run tests**

```bash
pytest tests/unit/test_sms.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/telephony/sms.py src/queue/tasks.py tests/unit/test_sms.py
git commit -m "feat: SMS fallback outreach with scheduling link"
```

---

## Task 18: Audit Logging

**Files:**
- Create: `src/analytics/audit.py`
- Test: `tests/unit/test_audit.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_audit.py
from unittest.mock import MagicMock, call
from src.analytics.audit import AuditLogger
from src.db.models import AuditLog


def test_audit_logger_writes_event():
    mock_db = MagicMock()
    logger = AuditLogger(db=mock_db)
    logger.log(
        entity_type="referral",
        entity_id=1,
        event_type="referral_received",
        event_data={"study_id": "STUDY-001"},
    )
    mock_db.add.assert_called_once()
    entry = mock_db.add.call_args[0][0]
    assert isinstance(entry, AuditLog)
    assert entry.entity_type == "referral"
    assert entry.event_type == "referral_received"


def test_audit_logger_records_call_events():
    mock_db = MagicMock()
    logger = AuditLogger(db=mock_db)
    logger.log_call_event(
        call_session_id=42,
        event_type="call_answered",
        data={"duration": 120},
    )
    mock_db.add.assert_called_once()
    entry = mock_db.add.call_args[0][0]
    assert entry.entity_type == "call_session"
    assert entry.entity_id == 42
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_audit.py -v
```

**Step 3: Implement**

```python
# src/analytics/audit.py
from datetime import datetime
from sqlalchemy.orm import Session
from src.db.models import AuditLog


class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    def log(self, entity_type: str, entity_id: int, event_type: str, event_data: dict = {}):
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            event_data=event_data,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()

    def log_call_event(self, call_session_id: int, event_type: str, data: dict = {}):
        self.log(
            entity_type="call_session",
            entity_id=call_session_id,
            event_type=event_type,
            event_data=data,
        )

    def log_referral_event(self, referral_id: int, event_type: str, data: dict = {}):
        self.log(
            entity_type="referral",
            entity_id=referral_id,
            event_type=event_type,
            event_data=data,
        )
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_audit.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/analytics/ tests/unit/test_audit.py
git commit -m "feat: audit logging for all call and referral events"
```

---

## Task 19: Analytics Metrics Capture

**Files:**
- Create: `src/analytics/metrics.py`
- Test: `tests/unit/test_metrics.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_metrics.py
from unittest.mock import MagicMock
from src.analytics.metrics import MetricsCollector


def test_metrics_collector_calculates_contact_rate():
    mock_db = MagicMock()
    collector = MetricsCollector(db=mock_db)

    mock_db.execute.return_value.fetchone.return_value = (100, 45)  # total, answered
    rate = collector.contact_rate(study_id="STUDY-001")
    assert rate == 0.45


def test_metrics_collector_calculates_time_to_first_contact():
    from datetime import datetime, timedelta
    mock_db = MagicMock()
    collector = MetricsCollector(db=mock_db)

    mock_db.execute.return_value.fetchone.return_value = (18.5,)  # avg minutes
    avg_minutes = collector.avg_time_to_first_contact(study_id="STUDY-001")
    assert avg_minutes == 18.5


def test_metrics_collector_calculates_prescreen_completion_rate():
    mock_db = MagicMock()
    collector = MetricsCollector(db=mock_db)

    mock_db.execute.return_value.fetchone.return_value = (80, 32)  # referrals, completions
    rate = collector.prescreen_completion_rate(study_id="STUDY-001")
    assert rate == 0.40
```

**Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_metrics.py -v
```

**Step 3: Implement**

```python
# src/analytics/metrics.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional


class MetricsCollector:
    """Computes pilot success metrics from the database."""

    def __init__(self, db: Session):
        self.db = db

    def contact_rate(self, study_id: str) -> float:
        """Percentage of referrals where patient was successfully reached."""
        row = self.db.execute(text("""
            SELECT COUNT(DISTINCT r.id) as total,
                   COUNT(DISTINCT CASE WHEN cs.outcome = 'answered' THEN r.id END) as answered
            FROM referrals r
            LEFT JOIN outreach_jobs oj ON oj.referral_id = r.id
            LEFT JOIN call_sessions cs ON cs.outreach_job_id = oj.id
            WHERE r.study_id = :study_id
        """), {"study_id": study_id}).fetchone()
        if not row or row[0] == 0:
            return 0.0
        return row[1] / row[0]

    def avg_time_to_first_contact(self, study_id: str) -> float:
        """Average minutes from referral creation to first answered call."""
        row = self.db.execute(text("""
            SELECT AVG(EXTRACT(EPOCH FROM (cs.started_at - r.created_at)) / 60)
            FROM referrals r
            JOIN outreach_jobs oj ON oj.referral_id = r.id
            JOIN call_sessions cs ON cs.outreach_job_id = oj.id
            WHERE r.study_id = :study_id
              AND cs.outcome = 'answered'
              AND oj.attempt_number = 1
        """), {"study_id": study_id}).fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    def prescreen_completion_rate(self, study_id: str) -> float:
        """Percentage of referrals that completed the pre-screen."""
        row = self.db.execute(text("""
            SELECT COUNT(DISTINCT r.id) as total,
                   COUNT(DISTINCT CASE WHEN cs.final_state = 'scheduling' OR cs.final_state = 'completed' THEN r.id END) as completed
            FROM referrals r
            LEFT JOIN outreach_jobs oj ON oj.referral_id = r.id
            LEFT JOIN call_sessions cs ON cs.outreach_job_id = oj.id
            WHERE r.study_id = :study_id
        """), {"study_id": study_id}).fetchone()
        if not row or row[0] == 0:
            return 0.0
        return row[1] / row[0]

    def answer_rate_by_hour(self, study_id: str) -> dict:
        """Returns dict of {hour: answer_rate} to find best contact windows."""
        rows = self.db.execute(text("""
            SELECT EXTRACT(HOUR FROM cs.started_at) as hour,
                   COUNT(*) as attempts,
                   SUM(CASE WHEN cs.outcome = 'answered' THEN 1 ELSE 0 END) as answered
            FROM referrals r
            JOIN outreach_jobs oj ON oj.referral_id = r.id
            JOIN call_sessions cs ON cs.outreach_job_id = oj.id
            WHERE r.study_id = :study_id
            GROUP BY hour
            ORDER BY hour
        """), {"study_id": study_id}).fetchall()
        return {
            int(row.hour): row.answered / row.attempts if row.attempts > 0 else 0.0
            for row in rows
        }
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_metrics.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/analytics/metrics.py tests/unit/test_metrics.py
git commit -m "feat: analytics metrics for contact rate, time to contact, pre-screen completion"
```

---

## Task 20: Full Test Suite & End-to-End Smoke Test

**Files:**
- Create: `tests/integration/test_end_to_end.py`
- Create: `tests/conftest.py`

**Step 1: Create conftest.py with test database**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
from src.api.main import app
from src.api.dependencies import get_db

TEST_DATABASE_URL = "postgresql://lynd:lynd_dev@localhost:5432/lynd_test"

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()
```

**Step 2: Write end-to-end smoke test**

```python
# tests/integration/test_end_to_end.py
import pytest
from unittest.mock import patch, MagicMock


def test_full_referral_intake_creates_db_records(client, db_session):
    """Smoke test: referral in → patient + referral + outreach jobs in DB."""
    from src.db.models import Patient, Referral, OutreachJob

    with patch("src.queue.tasks.queue_outreach.delay") as mock_queue:
        response = client.post("/api/v1/referrals", json={
            "patient": {
                "first_name": "Test",
                "last_name": "Patient",
                "phone": "+15551234567",
                "date_of_birth": "1975-06-15",
            },
            "study_id": "SMOKE-001",
            "referring_provider": "Dr. Test",
        })

    assert response.status_code == 201
    referral_id = response.json()["referral_id"]
    mock_queue.assert_called_once_with(referral_id)

    referral = db_session.query(Referral).filter(Referral.id == referral_id).first()
    assert referral is not None
    assert referral.study_id == "SMOKE-001"

    patient = db_session.query(Patient).filter(Patient.id == referral.patient_id).first()
    assert patient.first_name == "Test"


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

**Step 4: Run with coverage**

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

Expected: >70% coverage

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: integration tests and full test suite"
```

---

## Task 21: Coordinator Dashboard (Retool)

**Note:** Do NOT build a custom dashboard for V1. Use Retool instead.

**Step 1: Set up Retool**

1. Go to [retool.com](https://retool.com) and create a free account
2. Connect to your PostgreSQL database as a Resource

**Step 2: Create "Referrals" page in Retool**

Add a Table component with query:
```sql
SELECT
    r.id,
    p.first_name || ' ' || p.last_name as patient_name,
    p.phone,
    r.study_id,
    r.status,
    r.created_at,
    COUNT(cs.id) as call_attempts,
    MAX(cs.outcome) as last_call_outcome,
    MAX(cs.final_state) as conversation_reached
FROM referrals r
JOIN patients p ON p.id = r.patient_id
LEFT JOIN outreach_jobs oj ON oj.referral_id = r.id
LEFT JOIN call_sessions cs ON cs.outreach_job_id = oj.id
GROUP BY r.id, p.first_name, p.last_name, p.phone, r.study_id, r.status, r.created_at
ORDER BY r.created_at DESC
```

**Step 3: Create "Call Transcripts" page**

Add a Table for call sessions and a Text component to display transcript JSON.

Query:
```sql
SELECT
    cs.id,
    cs.twilio_call_sid,
    cs.outcome,
    cs.duration_seconds,
    cs.final_state,
    cs.transcript,
    cs.started_at,
    p.first_name || ' ' || p.last_name as patient_name
FROM call_sessions cs
JOIN outreach_jobs oj ON oj.id = cs.outreach_job_id
JOIN referrals r ON r.id = oj.referral_id
JOIN patients p ON p.id = r.patient_id
ORDER BY cs.started_at DESC
```

**Step 4: Create "Metrics" page**

Add stat components showing:
- Contact rate: `SELECT COUNT(*) FILTER (WHERE outcome='answered')::float / COUNT(*) FROM call_sessions`
- Avg time to contact: use the query from `MetricsCollector.avg_time_to_first_contact`
- Pre-screen completion rate

**Step 5: Share dashboard URL with study coordinators**

No code commit needed — Retool handles the UI.

---

## Task 22: Deployment to AWS

**Files:**
- Create: `.github/workflows/deploy.yml` (optional CI)
- Create: `Dockerfile` (already exists, verify it works)

**Step 1: Build and verify Docker image**

```bash
docker build -t lynd-voice-agent .
docker run --env-file .env lynd-voice-agent uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Expected: App starts cleanly

**Step 2: Set up AWS infrastructure (manual, one-time)**

Required AWS services:
- **ECS Fargate** — runs the FastAPI app and Celery worker
- **RDS PostgreSQL 15** — with pgvector extension enabled (`CREATE EXTENSION vector;`)
- **ElastiCache Redis** — for Celery broker
- **ALB** — routes HTTPS traffic to ECS

Use AWS Console or Terraform. For a V1 pilot, manual setup via Console is fine.

**Step 3: Configure environment variables in AWS**

Store all `.env` values in **AWS Systems Manager Parameter Store** (SecureString for secrets).

**Step 4: Configure Twilio webhook URLs**

In Twilio Console, your webhook base URL will be your ALB domain (e.g., `https://api.lynd.com`).

Ensure the ALB has an SSL certificate (use AWS Certificate Manager — free).

**Step 5: Run database migrations on RDS**

```bash
DATABASE_URL=postgresql://lynd:<password>@<rds-endpoint>:5432/lynd alembic upgrade head
```

**Step 6: Smoke test production**

```bash
curl -X POST https://api.lynd.com/api/v1/referrals \
  -H "Content-Type: application/json" \
  -d '{"patient": {"first_name": "Test", "last_name": "Patient", "phone": "+15551234567", "date_of_birth": "1975-06-15"}, "study_id": "PILOT-001"}'
```

Expected: 201 with referral_id

**Step 7: Commit deployment config**

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore: verify deployment config for AWS"
```

---

## Pre-Pilot Checklist

Before going live with real patients:

- [ ] Twilio account verified and phone number purchased
- [ ] IRB script ingested via `scripts/ingest_irb_script.py`
- [ ] Pre-screen questions updated in `src/telephony/call_handler.py` DEFAULT_PRESCREEN_QUESTIONS
- [ ] ElevenLabs voice selected and tested (choose a warm, professional voice)
- [ ] Calendly event created and URL configured in `.env`
- [ ] Retool dashboard shared with coordinators
- [ ] Test call end-to-end with a team member's phone
- [ ] Confirm voicemail message plays correctly (no PHI)
- [ ] Confirm call recording is stored and accessible
- [ ] Confirm Retool dashboard shows call data
- [ ] Coordinator escalation procedure documented

---

## Open Engineering Decisions

1. **Embedding provider for RAG** — Choose Voyage AI or OpenAI `text-embedding-3-small`. Add to `pyproject.toml` and implement `_embed()` in `knowledge_base.py` and `retrieval.py`.

2. **Latency testing** — After Task 16, test real-time conversation latency. Target <1.5s turn-around. If latency is too high, fall back to Twilio `<Gather>` with `input="speech"` (simpler but less natural).

3. **PHI handling** — DOB is stored in plaintext in V1. For production, encrypt at rest using AWS KMS. Flag for V2.

4. **Authentication** — The referral API has no auth in V1. Add API key auth before sharing the endpoint externally.

5. **Calendly vs custom scheduling** — If Calendly integration proves too rigid for study coordinators, consider Cal.com (self-hosted, more flexible).
