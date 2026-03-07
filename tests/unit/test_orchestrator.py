from unittest.mock import MagicMock
from src.outreach.orchestrator import OutreachOrchestrator, OutreachCadence
from datetime import timedelta


def test_cadence_generates_correct_attempt_schedule():
    cadence = OutreachCadence.default()
    assert len(cadence.attempts) == 4  # 3 voice + 1 SMS
    assert cadence.attempts[0].delay_minutes == 0    # immediate
    assert cadence.attempts[1].delay_minutes == 30   # retry after 30 min
    assert cadence.attempts[2].delay_minutes == 240  # retry 4 hours later
    assert cadence.attempts[3].channel == "sms"      # SMS fallback


def test_orchestrator_builds_correct_outreach_plan():
    orch = OutreachOrchestrator(db=MagicMock())
    plan = orch.build_outreach_plan(referral_id=1)
    assert len(plan) == 4
    assert plan[0]["channel"] == "voice"
    assert plan[0]["delay_minutes"] == 0
    assert plan[3]["channel"] == "sms"


def test_orchestrator_creates_outreach_jobs():
    mock_db = MagicMock()
    mock_referral = MagicMock(id=1, patient_id=1)

    orch = OutreachOrchestrator(db=mock_db)
    jobs = orch.create_outreach_jobs(mock_referral)
    assert len(jobs) == 4  # 3 voice + 1 SMS
    assert mock_db.add.call_count == 4
    mock_db.commit.assert_called_once()


def test_outreach_plan_has_sms_fallback():
    orch = OutreachOrchestrator(db=MagicMock())
    plan = orch.build_outreach_plan(referral_id=1)
    channels = [step["channel"] for step in plan]
    assert "sms" in channels
