import audioop
import logging
from typing import Generator
from elevenlabs import ElevenLabs

logger = logging.getLogger(__name__)


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
            model_id="eleven_turbo_v2_5",
            output_format="pcm_16000",
        )
        pcm_data = b"".join(audio_chunks)

        if not pcm_data:
            return b""

        # Downsample 16kHz -> 8kHz, then convert linear16 -> mulaw for Twilio
        downsampled, _ = audioop.ratecv(pcm_data, 2, 1, 16000, 8000, None)
        mulaw_data = audioop.lin2ulaw(downsampled, 2)
        return mulaw_data

    def synthesize_stream(self, text: str) -> Generator[bytes, None, None]:
        """Streams mulaw audio chunks as they arrive from ElevenLabs.

        Yields mulaw-encoded chunks suitable for Twilio, with lower
        time-to-first-byte than synthesize().
        """
        audio_chunks = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_turbo_v2_5",
            output_format="pcm_16000",
        )

        pcm_buffer = b""
        # Process in ~4KB PCM chunks (250ms at 16kHz 16-bit)
        CHUNK_SIZE = 4000

        for chunk in audio_chunks:
            pcm_buffer += chunk
            while len(pcm_buffer) >= CHUNK_SIZE:
                pcm_piece = pcm_buffer[:CHUNK_SIZE]
                pcm_buffer = pcm_buffer[CHUNK_SIZE:]
                downsampled, _ = audioop.ratecv(pcm_piece, 2, 1, 16000, 8000, None)
                yield audioop.lin2ulaw(downsampled, 2)

        # Flush remaining buffer
        if pcm_buffer:
            downsampled, _ = audioop.ratecv(pcm_buffer, 2, 1, 16000, 8000, None)
            yield audioop.lin2ulaw(downsampled, 2)
