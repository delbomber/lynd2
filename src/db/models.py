import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


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
    communication_preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    referrals = relationship("Referral", back_populates="patient")


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    study_id = Column(String(100), nullable=False)
    referring_provider = Column(String(200))
    referral_metadata = Column(JSON, default=dict)
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
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class IRBKnowledgeEntry(Base):
    __tablename__ = "irb_knowledge"
    id = Column(Integer, primary_key=True)
    key = Column(String(200), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    study_id = Column(String(100))
    embedding = Column(Vector(1536))  # pgvector embedding dimension
    created_at = Column(DateTime, default=datetime.utcnow)
