import logging
import re
from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


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
    def get_opening_prompt(self, context: ConversationContext) -> str:
        first_name = context.patient_name.split()[0]
        return (
            f"Hi, may I please speak with {first_name}? "
            f"Great — to make sure I'm speaking with the right person, "
            f"could you please confirm your date of birth?"
        )

    def verify_dob(self, patient_said: str, actual_dob: str, api_key: str) -> bool:
        """Uses Claude to parse the spoken DOB and compare to record."""
        claude = ClaudeClient(api_key=api_key)
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
        # If the transcript doesn't look like a date at all (background noise,
        # greetings like "hello", "Miss Hurd", etc.), don't count it as an attempt
        if not _looks_like_dob(patient_text):
            logger.info(
                "Ignoring non-DOB utterance (attempt not counted): %r", patient_text
            )
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "I'm sorry, could you please share your date of birth "
                "so I can verify your identity?",
            )

        if self.verify_dob(
            patient_said=patient_text, actual_dob=actual_dob, api_key=api_key
        ):
            context.identity_verified = True
            return (
                ConversationState.INTRODUCTION,
                "Thank you for confirming. I'm calling from Lynd Clinical "
                "about a research opportunity your provider referred you for. "
                "Do you have a few minutes to hear about it?",
            )
        elif attempt < MAX_DOB_ATTEMPTS:
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "I'm sorry, that didn't match our records. Could you try again "
                "with your date of birth — month, day, and year?",
            )
        else:
            return (
                ConversationState.ESCALATION,
                "I'm having trouble verifying your information. "
                "Let me connect you with a member of our study team who can help.",
            )
