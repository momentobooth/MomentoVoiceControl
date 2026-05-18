"""
stt/transcriber.py -- Parakeet TDT via Docker API with Debug Logging.

This version replaces local Faster-Whisper with a connection to the
Parakeet TDT 0.6B v3 container and includes optional
disk-logging for audio debugging.
"""
from __future__ import annotations

import io
import os
import re
import time
import threading
import numpy as np
from scipy.io import wavfile
from openai import OpenAI

from emulation.scope_states import Example

# API Settings
PARAKEET_BASE_URL = os.getenv("STT_URL", "http://localhost:5092/v1")
PARAKEET_MODEL = "parakeet-tdt-0.6b-v3" #
API_KEY = "sk-no-key-required"

# Debug Settings: Set to a path (e.g., "debug_audio") to save incoming clips
DEBUG_SAVE_PATH = os.getenv("STT_DEBUG_PATH", None)

class Transcriber:
    """
    Wraps the Parakeet TDT API; designed for single worker thread usage.
    """

    def __init__(self, model_size: str = PARAKEET_MODEL) -> None:
        print(f"[STT] Connecting to Parakeet TDT at {PARAKEET_BASE_URL}...")
        self.client = OpenAI(
            base_url=PARAKEET_BASE_URL,
            api_key=API_KEY
        )
        self._model = model_size
        self._hotwords: str | None = None
        self._lock = threading.Lock()

        if DEBUG_SAVE_PATH and not os.path.exists(DEBUG_SAVE_PATH):
            os.makedirs(DEBUG_SAVE_PATH)
            print(f"[STT] Debug mode active. Saving clips to: {DEBUG_SAVE_PATH}")

        print("[STT] Client ready.")

    def _save_debug_audio(self, audio_int16: np.ndarray) -> None:
        """Helper to write the raw audio to disk for inspection."""
        if not DEBUG_SAVE_PATH:
            return

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(DEBUG_SAVE_PATH, f"rec_{timestamp}_{int(time.time())}.wav")
        wavfile.write(filename, 16000, audio_int16)

    def update_hotwords(self, registry) -> None:
        """
        Rebuild the prompt. For Parakeet TDT, a focused list of
        phrases or a 'context sentence' often works better than
        a raw comma-separated dump of every single word.
        """
        # Strategy: Use a prefix that tells the model what to expect.
        # This helps the Transducer set the right context.
        prefix = "The following are voice commands: "

        unique_commands: set[str] = set()
        for cmd in registry.commands:
            for example in cmd.examples:
                # Clean placeholders like {device}
                clean = re.sub(r"\{\w+\}", "", example.phrase).lower().strip()
                if len(clean) > 2:
                    unique_commands.add(clean)

        # We sort them to keep the prompt consistent
        command_list = ", ".join(sorted(unique_commands))

        with self._lock:
            # We wrap it in a 'contextual' sentence
            self._hotwords = f"{prefix}{command_list}."

        print(f"[STT] Context prompt updated: {self._hotwords}")

    def transcribe(self, audio: np.ndarray) -> str | None:
        """
        Transcribes audio using the Parakeet TDT model via API.
        """
        # Convert float32 to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Optional: Save to disk for debugging
        self._save_debug_audio(audio_int16)

        # Convert to WAV in memory for the API
        byte_io = io.BytesIO()
        wavfile.write(byte_io, 16000, audio_int16)
        byte_io.seek(0)
        byte_io.name = "audio.wav"

        try:
            with self._lock:
                prompt = self._hotwords

            response = self.client.audio.transcriptions.create(
                model=self._model,
                file=byte_io,
                prompt=prompt,
                response_format="text"
            )

            if not response:
                return None

            # Consistent cleanup logic
            text = response.strip()
            to_remove = [",", ".", ";"]
            for rm in to_remove:
                text = text.replace(rm, "")

            if text.startswith(("[", "(")):
                return None

            return text.lower().strip()

        except Exception as e:
            print(f"[STT] API Error: {e}")
            return None
