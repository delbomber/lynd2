from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent


class IntroductionState:
    def get_opening_prompt(self, context: ConversationContext) -> str:
        return (
            "I'm calling from Lynd Clinical about a research opportunity "
            "your provider referred you for. We're conducting a clinical study "
            "and your doctor thought you might qualify. "
            "Do you have a couple of minutes to learn more?"
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext, api_key: str
    ) -> Tuple[ConversationState, str]:
        detector = IntentDetector(api_key=api_key)
        intent = detector.detect(patient_text, state="introduction")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "Of course — let me connect you with a member of our study team.",
            )
        elif intent == Intent.DENY:
            context.interest_level = "not_interested"
            return (
                ConversationState.COMPLETED,
                "No problem at all. Thank you for your time, and have a great day.",
            )
        else:
            context.interest_level = "interested"
            return (
                ConversationState.PRE_SCREEN,
                "Great, thank you! I just have a few quick questions to see if you may qualify. "
                "This should only take about two minutes.",
            )
