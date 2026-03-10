import logging
import re
from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


def _expand_title(name: str) -> str:
    """Expand abbreviations like 'Dr.' to 'Doctor' for clearer TTS pronunciation."""
    return re.sub(r'\bDr\.?\b', 'Doctor', name)


DOB_PARSE_SYSTEM = """Extract a date of birth from natural speech and return it in YYYY-MM-DD format.
Examples: 'January 15th 1980' -> '1980-01-15', 'the fifth of March, 85' -> '1985-03-05',
'12/01/1982' -> '1982-12-01', 'december 1st 1982' -> '1982-12-01'
Return ONLY the date string. If you cannot parse a date, return 'UNKNOWN'."""

# Max real DOB attempts before escalation (doesn't count non-DOB noise)
MAX_DOB_ATTEMPTS = 3


def _looks_like_dob(text: str) -> bool:
    """Check if the text plausibly contains a date (has digits or month names)."""
    if re.search(r'\d', text):
        return True
    months = (
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
    )
    lower = text.lower()
    return any(m in lower for m in months)


class IdentityVerificationState:
    def __init__(self):
        self.greeting_confirmed = False

    def get_opening_prompt(self, context: ConversationContext) -> str:
        first_name = context.patient_name.split()[0]
        provider = _expand_title(context.referring_provider) if context.referring_provider else "Your doctor"
        return (
            f"Hi {first_name}, this is Sarah calling from Lynd Clinical. "
            f"{provider} recently referred you to us about a research study, "
            f"and I'm calling to follow up. Is now an okay time?"
        )

    def verify_dob(self, patient_said: str, actual_dob: str, api_key: str) -> bool:
        """Uses Claude to parse the spoken DOB and compare to record."""
        claude = ClaudeClient(api_key=api_key, model="claude-haiku-4-5-20251001")
        parsed = claude.complete(
            system=DOB_PARSE_SYSTEM,
            user=patient_said,
            max_tokens=20,
        ).strip()
        logger.info(
            "DOB verification: patient_said=%r, parsed=%r, actual=%r, match=%s",
            patient_said, parsed, actual_dob, parsed == actual_dob,
        )
        return parsed == actual_dob

    def handle_response(
        self,
        patient_text: str,
        context: ConversationContext,
        actual_dob: str,
        api_key: str,
        attempt: int = 1,
    ) -> Tuple[ConversationState, str]:
        # Phase 1: Wait for patient to confirm they are the right person
        if not self.greeting_confirmed:
            # Any response (yes, speaking, this is she, hello, etc.) confirms
            self.greeting_confirmed = True
            logger.info("Greeting confirmed, asking for DOB")
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "Great! Before I continue, could you please confirm your date of birth "
                "so I can make sure I'm speaking with the right person?",
            )

        # Phase 2: DOB verification
        # If the transcript doesn't look like a date at all (background noise,
        # greetings like "hello", etc.), don't count it as an attempt
        if not _looks_like_dob(patient_text):
            logger.info(
                "Ignoring non-DOB utterance (attempt not counted): %r", patient_text
            )
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "Sorry about that — could you share your date of birth for me?",
            )

        if self.verify_dob(
            patient_said=patient_text, actual_dob=actual_dob, api_key=api_key
        ):
            context.identity_verified = True
            provider = _expand_title(context.referring_provider) if context.referring_provider else "Your doctor"
            return (
                ConversationState.INTRODUCTION,
                f"Perfect, thank you! So as I mentioned, {provider} referred you "
                "for a clinical research study we're coordinating. It would involve "
                "a short screening call with one of our study coordinators. "
                "Would you like to hear a little more about it?",
            )
        elif attempt < MAX_DOB_ATTEMPTS:
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "I may have heard that incorrectly. Could you please confirm "
                "your date of birth again — month, day, and year?",
            )
        else:
            return (
                ConversationState.ESCALATION,
                "I'm having a bit of trouble verifying that. "
                "Let me connect you with one of our study coordinators who can help.",
            )
