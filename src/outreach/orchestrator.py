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
            AttemptConfig(delay_minutes=0, channel="voice"),      # immediate call
            AttemptConfig(delay_minutes=30, channel="voice"),     # retry 30 min later
            AttemptConfig(delay_minutes=240, channel="voice"),    # retry 4 hours later
            AttemptConfig(delay_minutes=300, channel="sms"),      # SMS fallback 5 hours later
        ])


class OutreachOrchestrator:
    def __init__(self, db: Session, study_id: str = ""):
        self.db = db
        # Demo referrals get a single immediate call — no retries
        if study_id.startswith("DEMO"):
            self.cadence = OutreachCadence(attempts=[
                AttemptConfig(delay_minutes=0, channel="voice"),
            ])
        else:
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
