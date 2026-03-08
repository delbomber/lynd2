# src/audio/stt.py
from __future__ import annotations

import asyncio
import logging
import threading
import queue
from typing import Callable, Optional, Awaitable

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)

# Sentinel to signal the thread to stop
_STOP = b"__STOP__"


class DeepgramTranscriber:
    """Wraps Deepgram streaming STT for real-time call transcription.

    Deepgram SDK v6 uses a synchronous WebSocket client, so we run it in a
    background thread and bridge audio/transcripts via queues.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.on_transcript: Optional[Callable[[str], Awaitable[None]]] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _parse_transcript_response(self, response) -> Optional[str]:
        """Extracts final transcript text from Deepgram response."""
        data = response if isinstance(response, dict) else response.to_dict()
        if not data.get("is_final"):
            return None
        alternatives = data.get("channel", {}).get("alternatives", [])
        if not alternatives:
            return None
        text = alternatives[0].get("transcript", "").strip()
        return text if text else None

    def _run_deepgram(self):
        """Runs in a background thread — opens Deepgram connection and feeds audio."""
        client = DeepgramClient(api_key=self.api_key)
        try:
            with client.listen.v1.connect(
                model="nova-2",
                language="en-US",
                smart_format="true",
                encoding="mulaw",
                channels="1",
                sample_rate="8000",
                interim_results="false",
                endpointing="500",
            ) as conn:
                # Register transcript handler
                def on_message(result, **kwargs):
                    text = self._parse_transcript_response(result)
                    if text and self.on_transcript and self._loop:
                        asyncio.run_coroutine_threadsafe(
                            self.on_transcript(text), self._loop
                        )

                conn.on("transcript", on_message)

                # Feed audio from queue until stopped
                while True:
                    try:
                        audio = self._audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if audio is _STOP:
                        break
                    conn.send(audio)
        except Exception:
            logger.exception("Deepgram thread error")

    async def start(self, on_transcript: Callable[[str], Awaitable[None]]):
        """Starts the Deepgram connection in a background thread."""
        self.on_transcript = on_transcript
        self._loop = asyncio.get_running_loop()
        self._thread = threading.Thread(target=self._run_deepgram, daemon=True)
        self._thread.start()

    async def send_audio(self, audio_bytes: bytes):
        """Queues audio bytes for the Deepgram thread."""
        self._audio_queue.put(audio_bytes)

    async def finish(self):
        """Signals the Deepgram thread to stop."""
        self._audio_queue.put(_STOP)
        if self._thread:
            self._thread.join(timeout=5)
