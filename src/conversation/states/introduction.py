from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent


class IntroductionState:
    def get_opening_prompt(self, context: ConversationContext) -> str:
        provider = context.referring_provider or "Your doctor"
        return (
            f"{provider} referred you for a clinical research study we're coordinating. "
            "It would involve a short screening call with one of our study coordinators. "
            "Would you like to hear a little more about the study?"
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext, api_key: str
    ) -> Tuple[ConversationState, str]:
        detector = IntentDetector(api_key=api_key)
        intent = detector.detect(patient_text, state="introduction")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "Of course — let me connect you with one of our study coordinators.",
            )
        elif intent == Intent.DENY:
            context.interest_level = "not_interested"
            return (
                ConversationState.COMPLETED,
                "No problem at all. If anything changes, your doctor's office "
                "can always put you back in touch with us. Have a great day!",
            )
        else:
            context.interest_level = "interested"
            return (
                ConversationState.PRE_SCREEN,
                "Great! I'll ask a few quick questions that help us see whether "
                "the study might be a good fit. This should only take about two minutes.",
            )
