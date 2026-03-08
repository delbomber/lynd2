import pytest
from unittest.mock import patch, MagicMock
from src.llm.intent import IntentDetector, Intent


def test_known_intents_are_defined():
    assert Intent.ESCALATE
    assert Intent.CONFIRM
    assert Intent.DENY
    assert Intent.SCHEDULE
    assert Intent.CALLBACK
    assert Intent.UNCLEAR


def test_intent_detector_classifies_escalation():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "ESCALATE"
        intent = detector.detect("Can I speak to a real person please?", state="pre_screen")
        assert intent == Intent.ESCALATE


def test_intent_detector_classifies_confirmation():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "CONFIRM"
        intent = detector.detect("Yes, that's right", state="identity_verification")
        assert intent == Intent.CONFIRM


def test_intent_detector_classifies_denial():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "DENY"
        intent = detector.detect("No I'm not interested", state="introduction")
        assert intent == Intent.DENY


def test_intent_detector_classifies_schedule():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "SCHEDULE"
        intent = detector.detect("I'd like to schedule for tomorrow", state="scheduling")
        assert intent == Intent.SCHEDULE


def test_intent_detector_classifies_callback():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "CALLBACK"
        intent = detector.detect("Call me back later tonight", state="scheduling")
        assert intent == Intent.CALLBACK


def test_intent_detector_handles_unknown_response():
    detector = IntentDetector(api_key="test_key")
    with patch.object(detector, "_call_claude") as mock:
        mock.return_value = "SOMETHING_WEIRD"
        intent = detector.detect("blah blah", state="pre_screen")
        assert intent == Intent.UNCLEAR
