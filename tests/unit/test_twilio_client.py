from unittest.mock import patch, MagicMock
from src.telephony.client import TwilioClient


def test_make_outbound_call_calls_twilio_api():
    with patch("src.telephony.client.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        mock_twilio.calls.create.return_value = MagicMock(sid="CA123")

        client = TwilioClient(
            account_sid="ACtest",
            auth_token="token",
            from_number="+15550000000",
        )
        sid = client.make_outbound_call(
            to="+15551234567",
            webhook_url="https://lynd.com/webhooks/call/1/answer",
            status_callback_url="https://lynd.com/webhooks/call/1/status",
            machine_detection=True,
        )
        assert sid == "CA123"
        mock_twilio.calls.create.assert_called_once()


def test_make_outbound_call_passes_machine_detection():
    with patch("src.telephony.client.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        mock_twilio.calls.create.return_value = MagicMock(sid="CA456")

        client = TwilioClient(
            account_sid="ACtest",
            auth_token="token",
            from_number="+15550000000",
        )
        client.make_outbound_call(
            to="+15551234567",
            webhook_url="https://lynd.com/webhooks/call/1/answer",
            status_callback_url="https://lynd.com/webhooks/call/1/status",
            machine_detection=True,
        )
        call_kwargs = mock_twilio.calls.create.call_args.kwargs
        assert call_kwargs.get("machine_detection") == "Enable"


def test_send_sms_returns_sid():
    with patch("src.telephony.client.Client") as MockClient:
        mock_twilio = MagicMock()
        MockClient.return_value = mock_twilio
        mock_twilio.messages.create.return_value = MagicMock(sid="SM789")

        client = TwilioClient(
            account_sid="ACtest",
            auth_token="token",
            from_number="+15550000000",
        )
        sid = client.send_sms(to="+15551234567", body="Hello from Lynd")
        assert sid == "SM789"
        mock_twilio.messages.create.assert_called_once_with(
            to="+15551234567",
            from_="+15550000000",
            body="Hello from Lynd",
        )
