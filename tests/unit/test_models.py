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
