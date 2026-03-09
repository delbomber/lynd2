from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.db.models import ConversationState

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

ALWAYS_ALLOWED = {ConversationState.ESCALATION, ConversationState.COMPLETED}


@dataclass
class ConversationContext:
    patient_name: str
    study_id: str
    referring_provider: str = ""
    identity_verified: bool = False
    interest_level: Optional[str] = None
    scheduling_outcome: Optional[str] = None
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
