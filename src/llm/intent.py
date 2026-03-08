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
