from src.conversation.state_machine import ConversationContext


class EscalationState:
    def get_handoff_message(self) -> str:
        return (
            "Let me connect you with one of our study coordinators "
            "who can help with that. One moment please."
        )

    def get_voicemail_handoff_message(self) -> str:
        return (
            "One of our study coordinators will follow up with you shortly. "
            "Thank you for your time."
        )
