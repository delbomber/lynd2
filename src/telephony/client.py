from twilio.rest import Client


class TwilioClient:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def make_outbound_call(
        self,
        to: str,
        webhook_url: str,
        status_callback_url: str,
        machine_detection: bool = True,
    ) -> str:
        """Initiates an outbound call and returns Twilio call SID."""
        kwargs = dict(
            to=to,
            from_=self.from_number,
            url=webhook_url,
            status_callback=status_callback_url,
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            record=True,
        )
        if machine_detection:
            kwargs["machine_detection"] = "Enable"
            kwargs["machine_detection_timeout"] = 30

        call = self.client.calls.create(**kwargs)
        return call.sid

    def send_sms(self, to: str, body: str) -> str:
        """Sends an SMS and returns message SID."""
        message = self.client.messages.create(
            to=to,
            from_=self.from_number,
            body=body,
        )
        return message.sid
