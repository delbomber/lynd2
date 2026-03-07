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
    db.flush()  # get patient.id without committing

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
