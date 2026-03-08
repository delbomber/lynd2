from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.client import ClaudeClient


DOB_PARSE_SYSTEM = """Extract a date of birth from natural speech and return it in YYYY-MM-DD format.
Examples: 'January 15th 1980' -> '1980-01-15', 'the fifth of March, 85' -> '1985-03-05'
Return ONLY the date string. If you cannot parse a date, return 'UNKNOWN'."""


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
        return parsed == actual_dob

    def handle_response(
        self,
        patient_text: str,
        context: ConversationContext,
        actual_dob: str,
        api_key: str,
        attempt: int = 1,
    ) -> Tuple[ConversationState, str]:
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
        elif attempt < 2:
            return (
                ConversationState.IDENTITY_VERIFICATION,
                "I'm sorry, I didn't quite catch that. Could you try again "
                "with your date of birth?",
            )
        else:
            return (
                ConversationState.ESCALATION,
                "I'm having trouble verifying your information. "
                "Let me connect you with a member of our study team who can help.",
            )
