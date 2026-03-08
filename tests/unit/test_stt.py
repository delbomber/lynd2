# tests/unit/test_stt.py
import pytest
from src.audio.stt import DeepgramTranscriber


def test_transcriber_initializes_with_api_key():
    transcriber = DeepgramTranscriber(api_key="test_key")
    assert transcriber.api_key == "test_key"


def test_parse_transcript_returns_text_for_final():
    transcriber = DeepgramTranscriber(api_key="test_key")
    result = transcriber._extract_transcript({
        "channel": {
            "alternatives": [{"transcript": "Hello my name is Jane"}]
        },
        "is_final": True,
    })
    assert result == "Hello my name is Jane"


def test_parse_transcript_returns_none_for_non_final():
    transcriber = DeepgramTranscriber(api_key="test_key")
    result = transcriber._extract_transcript({
        "channel": {"alternatives": [{"transcript": "Hello"}]},
        "is_final": False,
    })
    assert result is None


def test_parse_transcript_returns_none_for_empty():
    transcriber = DeepgramTranscriber(api_key="test_key")
    result = transcriber._extract_transcript({
        "channel": {"alternatives": [{"transcript": ""}]},
        "is_final": True,
    })
    assert result is None


def test_parse_transcript_returns_none_for_missing_alternatives():
    transcriber = DeepgramTranscriber(api_key="test_key")
    result = transcriber._extract_transcript({
        "channel": {"alternatives": []},
        "is_final": True,
    })
    assert result is None
