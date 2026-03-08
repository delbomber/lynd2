from unittest.mock import patch, MagicMock
from src.audio.tts import ElevenLabsTTS


def test_tts_initializes():
    tts = ElevenLabsTTS(api_key="test_key", voice_id="voice_123")
    assert tts.voice_id == "voice_123"


def test_synthesize_returns_bytes():
    tts = ElevenLabsTTS(api_key="test_key", voice_id="voice_123")

    with patch.object(tts, "client") as mock_client:
        mock_client.text_to_speech.convert.return_value = iter([b"audio_chunk_1", b"audio_chunk_2"])

        audio = tts.synthesize("Hello, this is Lynd Clinical.")
        assert isinstance(audio, bytes)
        assert len(audio) > 0


def test_synthesize_calls_elevenlabs_with_correct_params():
    tts = ElevenLabsTTS(api_key="test_key", voice_id="voice_123")

    with patch.object(tts, "client") as mock_client:
        mock_client.text_to_speech.convert.return_value = iter([b"\x00" * 100])

        tts.synthesize("Hello")
        call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
        assert call_kwargs["voice_id"] == "voice_123"
        assert call_kwargs["text"] == "Hello"
