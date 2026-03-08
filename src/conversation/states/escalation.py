from src.conversation.state_machine import ConversationContext


class EscalationState:
    def get_handoff_message(self) -> str:
        return (
            "I'm going to connect you with a member of our study team "
            "who can answer your questions directly. Please hold for just a moment."
        )

    def get_voicemail_handoff_message(self) -> str:
        return (
            "Our study coordinator will follow up with you shortly. "
            "Thank you for your interest."
        )
