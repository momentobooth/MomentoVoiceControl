"""
audio/vad_loop.py — Continuous microphone capture with Silero VAD.

Produces complete utterance audio chunks (numpy arrays) via a queue.
The consumer (STT pipeline) reads from the queue asynchronously.

Tuning knobs
------------
SILENCE_GRACE_MS    : ms of silence after speech before we cut the utterance
MIN_SPEECH_MS       : discard utterances shorter than this (avoids clicks)
MAX_UTTERANCE_MS    : hard cap — forces a cut even if speech continues
PRE_ROLL_MS         : ms of silence to buffer before speech starts
"""
from __future__ import annotations
import queue
import threading
from collections import deque

import numpy as np
import pyaudio
import torch

from mqtt_bridge.bridge import MQTTBridge

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000          # Silero + Whisper both expect 16 kHz
CHUNK_MS = 32                 # VAD window; must be 32 ms for Silero
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)   # 512 samples

PRE_ROLL_MS = 400  # Buffer 400ms of audio before speech starts
PRE_ROLL_CHUNKS = PRE_ROLL_MS // CHUNK_MS

SILENCE_GRACE_MS = 600        # 600 ms of silence → end of utterance
SILENCE_GRACE_CHUNKS = SILENCE_GRACE_MS // CHUNK_MS

MIN_SPEECH_MS = 500
MIN_SPEECH_CHUNKS = MIN_SPEECH_MS // CHUNK_MS

MAX_UTTERANCE_MS = 10_000
MAX_UTTERANCE_CHUNKS = MAX_UTTERANCE_MS // CHUNK_MS

VAD_THRESHOLD = 0.5           # Silero probability threshold


def _load_silero_vad():
    """Download (first run) and return the Silero VAD model + get_speech_timestamps util."""
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        onnx=False,
    )
    return model


class VADLoop:
    """
    Captures audio from the default microphone and emits utterance chunks.

    Usage:
        vad = VADLoop(utterance_queue)
        vad.start()
        ...
        vad.stop()
    """

    def __init__(self, utterance_queue: queue.Queue, bridge: MQTTBridge) -> None:
        self._q = utterance_queue
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._model = _load_silero_vad()
        self._model.eval()
        print("[VAD] Silero model ready.")
        self._bridge = bridge

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[VAD] Listening…")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        # Detach the Python debugger trace from this thread.  PyCharm's
        # sys.settrace hook fires on every call into Torch C++ extensions,
        # making the VAD loop 20-50x slower under the debugger.  Removing the
        # trace here keeps the rest of the application (pipeline, resolver,
        # executor) fully steppable while this hot-path thread runs at full
        # speed.  You will not be able to set breakpoints inside _run itself,
        # but there is nothing here worth stepping through anyway.
        import sys
        sys.settrace(None)

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SAMPLES,
        )

        speech_chunks: list[np.ndarray] = []
        # This buffer keeps the most recent "silence" chunks
        pre_roll = deque(maxlen=PRE_ROLL_CHUNKS)

        silence_count = 0
        in_speech = False

        try:
            while not self._stop_event.is_set():
                raw = stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                if not self._bridge.is_listening:
                    continue
                pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                tensor = torch.from_numpy(pcm)

                prob: float = self._model(tensor, SAMPLE_RATE).item()
                is_speech = prob >= VAD_THRESHOLD

                if is_speech:
                    if not in_speech:
                        # START OF UTTERANCE: Grab the history from the pre_roll
                        speech_chunks.extend(list(pre_roll))
                        pre_roll.clear()
                        in_speech = True
                        self._bridge.show_notification("👂 Listening...", 1500)

                    silence_count = 0
                    speech_chunks.append(pcm)

                elif in_speech:
                    # We are currently in speech, but this specific chunk was quiet
                    speech_chunks.append(pcm)
                    silence_count += 1

                    if silence_count >= SILENCE_GRACE_CHUNKS:
                        self._emit(speech_chunks)
                        speech_chunks = []
                        silence_count = 0
                        in_speech = False
                else:
                    # Not in speech and hasn't started yet: just keep the history fresh
                    pre_roll.append(pcm)

                # Hard cap
                if in_speech and len(speech_chunks) >= MAX_UTTERANCE_CHUNKS:
                    self._emit(speech_chunks)
                    speech_chunks = []
                    silence_count = 0
                    in_speech = False

        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def _emit(self, chunks: list[np.ndarray]) -> None:
        if len(chunks) < MIN_SPEECH_CHUNKS:
            return
        audio = np.concatenate(chunks)
        try:
            self._bridge.show_notification("🤖 Processing...")
            self._q.put_nowait(audio)
        except queue.Full:
            print("[VAD] Warning: utterance queue full, dropping chunk.")
