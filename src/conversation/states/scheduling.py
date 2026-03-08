from typing import Tuple

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent


class SchedulingState:
    def __init__(self, calendly_event_url: str):
        self.calendly_event_url = calendly_event_url

    def get_opening_prompt(self) -> str:
        return (
            "The next step would be a short call with one of our study coordinators. "
            "Would you like me to send you a link so you can pick a time that works best?"
        )

    def handle_response(
        self, patient_text: str, context: ConversationContext, api_key: str
    ) -> Tuple[ConversationState, str]:
        detector = IntentDetector(api_key=api_key)
        intent = detector.detect(patient_text, state="scheduling")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "Of course — let me connect you with one of our study coordinators.",
            )
        elif intent in (Intent.SCHEDULE, Intent.CONFIRM):
            context.scheduling_outcome = "scheduled"
            return (
                ConversationState.COMPLETED,
                "I'll send you a text with a scheduling link so you can pick "
                "whatever time works best. Thanks so much for your time today, "
                "and we look forward to connecting you with the study team!",
            )
        elif intent == Intent.CALLBACK:
            context.scheduling_outcome = "callback_requested"
            return (
                ConversationState.COMPLETED,
                "No problem — I'll make a note that you'd like a callback, "
                "and one of our coordinators will reach out. Thanks for your time!",
            )
        else:
            context.scheduling_outcome = "declined"
            return (
                ConversationState.COMPLETED,
                "Totally understand. If anything changes, your doctor's office "
                "can always put you back in touch with us. Have a great day!",
            )
