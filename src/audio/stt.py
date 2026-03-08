# src/audio/stt.py
from __future__ import annotations

import asyncio
import base64
from typing import Callable, Optional, Awaitable

from deepgram import DeepgramClient


class DeepgramTranscriber:
    """Wraps Deepgram streaming STT for real-time call transcription."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = DeepgramClient(api_key=api_key)
        self.connection = None
        self.on_transcript: Optional[Callable[[str], Awaitable[None]]] = None

    def _parse_transcript_response(self, response: dict) -> Optional[str]:
        """Extracts final transcript text from Deepgram response dict."""
        if not response.get("is_final"):
            return None
        alternatives = response.get("channel", {}).get("alternatives", [])
        if not alternatives:
            return None
        text = alternatives[0].get("transcript", "").strip()
        return text if text else None

    async def start(self, on_transcript: Callable[[str], Awaitable[None]]):
        """Opens a Deepgram streaming connection with mulaw/8kHz settings."""
        self.on_transcript = on_transcript
        self.connection = self.client.listen.v1.connect(
            model="nova-2",
            language="en-US",
            smart_format=True,
            encoding="mulaw",
            channels=1,
            sample_rate=8000,
            interim_results=False,
            endpointing=500,
        )

        async def on_message(result, **kwargs):
            data = result if isinstance(result, dict) else result.to_dict()
            text = self._parse_transcript_response(data)
            if text and self.on_transcript:
                await self.on_transcript(text)

        self.connection.on("transcript", on_message)
        await self.connection.start()

    async def send_audio(self, audio_bytes: bytes):
        """Sends raw audio bytes to Deepgram."""
        if self.connection:
            await self.connection.send(audio_bytes)

    async def finish(self):
        """Closes the Deepgram connection."""
        if self.connection:
            await self.connection.finish()
