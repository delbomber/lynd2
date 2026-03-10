import enum
import re
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
        self.claude = ClaudeClient(api_key=api_key, model="claude-haiku-4-5-20251001")

    def _call_claude(self, patient_text: str, state: str) -> str:
        user_msg = f"Conversation state: {state}\nPatient said: \"{patient_text}\""
        return self.claude.complete(
            system=INTENT_SYSTEM_PROMPT,
            user=user_msg,
            max_tokens=10,
        )

    # Fast-path patterns that skip the LLM round-trip
    _CONFIRM_RE = re.compile(
        r'^\s*(yes|yeah|yep|yup|sure|okay|ok|absolutely|definitely|of course|sounds good|go ahead|please|uh huh|mhm)\b',
        re.IGNORECASE,
    )
    _DENY_RE = re.compile(
        r'^\s*(no|nah|nope|not interested|no thanks|no thank you|i\'m good)\b',
        re.IGNORECASE,
    )
    _ESCALATE_RE = re.compile(
        r'(speak to a person|speak to someone|talk to a human|real person|actual person|transfer me|connect me)',
        re.IGNORECASE,
    )

    def _fast_classify(self, patient_text: str) -> Intent | None:
        """Try to classify obvious intents without an LLM call."""
        if self._ESCALATE_RE.search(patient_text):
            return Intent.ESCALATE
        if self._DENY_RE.match(patient_text):
            return Intent.DENY
        if self._CONFIRM_RE.match(patient_text):
            return Intent.CONFIRM
        return None

    def detect(self, patient_text: str, state: str) -> Intent:
        fast = self._fast_classify(patient_text)
        if fast is not None:
            return fast
        raw = self._call_claude(patient_text, state).strip().upper()
        try:
            return Intent(raw)
        except ValueError:
            return Intent.UNCLEAR
