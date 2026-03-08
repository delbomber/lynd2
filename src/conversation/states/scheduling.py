from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent


class SchedulingState:
    def __init__(self, calendly_event_url: str):
        self.calendly_event_url = calendly_event_url

    def get_opening_prompt(self) -> str:
        return (
            "Would you like to schedule a brief screening call with our coordinator? "
            "I can also send you a link by text message so you can pick a time that works."
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext, api_key: str
    ) -> Tuple[ConversationState, str]:
        detector = IntentDetector(api_key=api_key)
        intent = detector.detect(patient_text, state="scheduling")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "I'll connect you with our study team right away.",
            )
        elif intent in (Intent.SCHEDULE, Intent.CONFIRM):
            context.scheduling_outcome = "scheduled"
            return (
                ConversationState.COMPLETED,
                "Wonderful! I'll send you a text message with a scheduling link "
                "so you can pick the time that works best. Thank you for your interest!",
            )
        elif intent == Intent.CALLBACK:
            context.scheduling_outcome = "callback_requested"
            return (
                ConversationState.COMPLETED,
                "Of course — I'll make a note that you'd like us to follow up. "
                "Our coordinator will reach out to find a good time. Thank you!",
            )
        else:
            context.scheduling_outcome = "declined"
            return (
                ConversationState.COMPLETED,
                "No problem at all. If you change your mind, our study team would be "
                "happy to hear from you. Thank you for your time today!",
            )
