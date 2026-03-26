"""
stt/transcriber.py -- Faster-Whisper speech-to-text.

Model selection guide (CPU, no GPU):
  tiny.en   ~80 MB    ~150-300 ms  -- default; good enough for short commands
  small.en  ~240 MB   ~600-900 ms  -- better accuracy, noticeable latency hit
  medium.en ~760 MB   ~1500+ ms    -- GPU strongly recommended at this size
  large-v3  ~1.5 GB   impractical on CPU

The dominant latency cost on short utterances is NOT the model size -- it is
Whisper's fixed 30-second mel spectrogram window.  Even a 2-word command gets
padded to 30 s before the encoder sees it.  Setting vad_filter=True tells
Faster-Whisper to run a secondary internal VAD pass and feed only the
speech-containing frames to the decoder, typically cutting latency 50-70%
for short clips.

CPU optimisation flags used:
  - vad_filter=True  (skip silent padding -- biggest single win)
  - beam_size=1      (greedy decode, ~2x faster than beam=5)
  - int8 quantisation (halves memory, ~20% faster on AVX2)
  - language="en"    (skips language detection overhead)
  - hotwords         (biases beam search toward known command vocabulary)
"""
from __future__ import annotations

import os
import re
import threading

import numpy as np
from faster_whisper import WhisperModel

DEFAULT_MODEL = "small.en"
LANGUAGE = "en"
THREADS = os.getenv("WHISPER_THREADS", 8)
BEAM_SIZE = 1
NO_SPEECH_THRESHOLD = 0.6
LOG_PROB_THRESHOLD = -1.0

# Internal VAD filter -- skip silent padding before the decoder sees the audio.
# This is the single biggest latency win for short utterances.
VAD_FILTER = False

# How strongly Whisper favours hotwords (1-20; 5 is a good starting point).
# Raise if short single-word commands are still misheard; lower if unrelated
# speech starts getting pulled toward command words.
HOTWORD_BIAS = 5.0


class Transcriber:
    """
    Wraps Faster-Whisper; designed to be called from a single worker thread.

    transcribe(audio_float32) -> str | None
      Returns the transcript or None if no speech was detected.

    update_hotwords(registry) is called automatically via a registry callback
    whenever the active command set changes.
    """

    def __init__(self, model_size: str = DEFAULT_MODEL) -> None:
        print(f"[STT] Loading Faster-Whisper {model_size} (CPU / int8)...")
        self._model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",      # fastest CPU mode; requires AVX2 (i7-6700K has it)
            cpu_threads=THREADS,
        )
        self._hotwords: str | None = None
        self._lock = threading.Lock()
        print("[STT] Model ready.")

    def update_hotwords(self, registry) -> None:
        """
        Rebuild the hotword string from the current registry.
        Called on the paho/registry thread; access is protected by a lock.

        Faster-Whisper accepts hotwords as a comma-separated string of phrases.
        We include every unique word from every example, deduplicated.
        Short words (<= 2 chars) are excluded -- too common to bias usefully.
        """
        BASE_HOTWORDS = "one,first,two,second,three,third,four,fourth,"

        words: set[str] = set()
        for cmd in registry.commands:
            for example in cmd.examples:
                clean = re.sub(r"\{\w+\}", "", example)
                for word in clean.lower().split():
                    word = word.strip(".,!?")
                    if len(word) > 2:
                        words.add(word)

        hotwords = BASE_HOTWORDS + ", ".join(sorted(words))
        with self._lock:
            self._hotwords = hotwords
        print(f"[STT] Hotwords updated: {hotwords}")

    def transcribe(self, audio: np.ndarray) -> str | None:
        """
        Parameters
        ----------
        audio : np.ndarray, float32, shape (N,), sample_rate=16000

        Returns
        -------
        Lowercase stripped transcript, or None if only silence / non-speech.
        """
        with self._lock:
            hotwords = self._hotwords

        segments, info = self._model.transcribe(
            audio,
            language=LANGUAGE,
            beam_size=BEAM_SIZE,
            no_speech_threshold=NO_SPEECH_THRESHOLD,
            log_prob_threshold=LOG_PROB_THRESHOLD,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=VAD_FILTER,
            hotwords=hotwords,
            # hotword_weight=HOTWORD_BIAS,
        )

        to_remove = [",", ".", ";"]

        parts = []
        for seg in segments:
            text = seg.text.strip()
            # Ensure there is no punctuation in our transcript
            for rm in to_remove:
                text = text.replace(rm, "")
            if text and not text.startswith(("[", "(")):
                parts.append(text)

        if not parts:
            return None

        return " ".join(parts).lower().strip()
