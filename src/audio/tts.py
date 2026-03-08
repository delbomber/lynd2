import audioop
from elevenlabs import ElevenLabs


class ElevenLabsTTS:
    """Wraps ElevenLabs TTS, outputting mulaw audio for Twilio Media Streams."""

    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.client = ElevenLabs(api_key=api_key)

    def synthesize(self, text: str) -> bytes:
        """Converts text to mulaw-encoded audio bytes for Twilio.

        ElevenLabs outputs PCM at 16kHz. Twilio Media Streams expects
        mulaw at 8kHz. This method handles the conversion.
        """
        audio_chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_turbo_v2",
            output_format="pcm_16000",
        )
        pcm_data = b"".join(audio_chunks)

        if not pcm_data:
            return b""

        # Downsample 16kHz -> 8kHz, then convert linear16 -> mulaw for Twilio
        downsampled, _ = audioop.ratecv(pcm_data, 2, 1, 16000, 8000, None)
        mulaw_data = audioop.lin2ulaw(downsampled, 2)
        return mulaw_data
