from typing import Tuple, List, Optional

from src.db.models import ConversationState
from src.conversation.state_machine import ConversationContext
from src.llm.intent import IntentDetector, Intent


class PreScreenState:
    def __init__(self, questions: List[dict]):
        self.questions = questions

    def get_current_question(self, index: int) -> Optional[dict]:
        if index < len(self.questions):
            return self.questions[index]
        return None

    def handle_response(
        self,
        patient_text: str,
        context: ConversationContext,
        question_index: int,
        api_key: str,
    ) -> Tuple[ConversationState, str, dict]:
        detector = IntentDetector(api_key=api_key)
        intent = detector.detect(patient_text, state="pre_screen")

        if intent == Intent.ESCALATE:
            return (
                ConversationState.ESCALATION,
                "I can connect you with one of our study coordinators who can answer that.",
                {},
            )

        question = self.questions[question_index]
        value = "yes" if intent == Intent.CONFIRM else "no" if intent == Intent.DENY else "unclear"
        context.record_response(
            question_key=question["key"],
            value=value,
            raw_text=patient_text,
        )

        next_index = question_index + 1
        if next_index < len(self.questions):
            next_question = self.questions[next_index]
            return (
                ConversationState.PRE_SCREEN,
                next_question["text"],
                {"next_question_index": next_index},
            )
        else:
            return (
                ConversationState.SCHEDULING,
                "Thank you for sharing that. Based on your answers, it sounds like "
                "you could be a good fit. The next step would be a short call with "
                "one of our study coordinators. Would you like me to send you a link "
                "so you can pick a time that works best?",
                {},
            )
