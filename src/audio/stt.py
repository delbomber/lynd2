# src/audio/stt.py
from __future__ import annotations

import asyncio
import json
import logging
import threading
import queue
from typing import Callable, Optional, Awaitable

from deepgram import DeepgramClient

logger = logging.getLogger(__name__)

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
        self._conn = None
        self._listening = False

    def _extract_transcript(self, response) -> Optional[str]:
        """Extracts final transcript text from Deepgram response."""
        if isinstance(response, bytes) or response is None:
            return None

        try:
            # SDK v6 returns Pydantic models (ListenV1Results)
            if hasattr(response, 'is_final'):
                if not response.is_final:
                    return None
                alternatives = response.channel.alternatives
                if not alternatives:
                    return None
                text = alternatives[0].transcript.strip()
                return text if text else None

            # Fallback for dict responses
            if isinstance(response, dict):
                if not response.get("is_final"):
                    return None
                alternatives = response.get("channel", {}).get("alternatives", [])
                if not alternatives:
                    return None
                text = alternatives[0].get("transcript", "").strip()
                return text if text else None
        except Exception:
            logger.exception("Error parsing Deepgram response")

        return None

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
                self._conn = conn

                # Import EventType from the module
                from deepgram.listen.v1.client import V1SocketClient
                import typing
                EventType = typing.get_type_hints(V1SocketClient.on)['event_name']

                # Register message handler
                def on_message(result):
                    logger.info("Deepgram message received: %s", type(result).__name__)
                    text = self._extract_transcript(result)
                    if text:
                        logger.info("Deepgram transcript: %s", text)
                        if self.on_transcript and self._loop:
                            asyncio.run_coroutine_threadsafe(
                                self.on_transcript(text), self._loop
                            )

                def on_error(error):
                    logger.error("Deepgram error: %s", error)

                conn.on(EventType.MESSAGE, on_message)
                conn.on(EventType.ERROR, on_error)

                logger.info("Deepgram connection established, starting listener")

                # Start a listener thread that processes incoming messages
                listener_thread = threading.Thread(
                    target=conn.start_listening, daemon=True
                )
                listener_thread.start()

                # Feed audio from queue until stopped
                audio_count = 0
                while True:
                    try:
                        audio = self._audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if audio is _STOP:
                        logger.info("STT stop signal received after %d audio chunks", audio_count)
                        break
                    try:
                        conn.send_media(audio)
                        audio_count += 1
                        if audio_count == 1:
                            logger.info("First audio chunk sent to Deepgram")
                        elif audio_count % 100 == 0:
                            logger.info("Sent %d audio chunks to Deepgram", audio_count)
                    except Exception:
                        logger.exception("Error sending audio to Deepgram")
                        break

                # Signal Deepgram to finalize
                try:
                    conn.send_close_stream()
                except Exception:
                    pass

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
