"""
stt/transcriber.py — Faster-Whisper speech-to-text.

Model selection guide for your i7-6700K (no GPU):
  tiny.en   ~80 MB    ~80 ms   — fastest, lower accuracy, good for quiet environments
  small.en  ~240 MB   ~300 ms  — best CPU trade-off  ← default
  medium.en ~760 MB   ~900 ms  — use when accuracy matters more than latency
  large-v3  ~1.5 GB   ~2500 ms — GPU recommended

CPU optimisation flags used:
  - beam_size=1  (greedy, halves compute vs beam=5)
  - int8 quantisation (halves memory + ~20% faster on AVX2)
  - language="en"  (skips language detection overhead)
"""
from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel

DEFAULT_MODEL = "small.en"

# Languages to force; set None to auto-detect (slower)
LANGUAGE = "en"

# Beam size 1 = greedy decode, ~2× faster than default beam=5
BEAM_SIZE = 1

# Suppress tokens that would be non-speech noise artifacts
NO_SPEECH_THRESHOLD = 0.6    # probability above which segment is marked non-speech
LOG_PROB_THRESHOLD = -1.0    # discard low-confidence segments


class Transcriber:
    """
    Wraps Faster-Whisper; designed to be called from a single worker thread.

    transcribe(audio_float32) → str | None
      Returns the transcript or None if no speech was detected.
    """

    def __init__(self, model_size: str = DEFAULT_MODEL) -> None:
        print(f"[STT] Loading Faster-Whisper {model_size} (CPU / int8)…")
        self._model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",      # fastest CPU mode; requires AVX2 (i7-6700K has it)
        )
        print("[STT] Model ready.")

    def transcribe(self, audio: np.ndarray) -> str | None:
        """
        Parameters
        ----------
        audio : np.ndarray, float32, shape (N,), sample_rate=16000

        Returns
        -------
        Lowercase stripped transcript, or None if only silence / non-speech.
        """
        segments, info = self._model.transcribe(
            audio,
            language=LANGUAGE,
            beam_size=BEAM_SIZE,
            no_speech_threshold=NO_SPEECH_THRESHOLD,
            log_prob_threshold=LOG_PROB_THRESHOLD,
            condition_on_previous_text=False,   # no context drift across utterances
            word_timestamps=False,              # saves ~10 ms; enable if you need word-level timing
        )

        parts = []
        for seg in segments:
            # Whisper sometimes emits background noise transcriptions starting with [ or (
            text = seg.text.strip()
            if text and not text.startswith(("[", "(")):
                parts.append(text)

        if not parts:
            return None

        return " ".join(parts).lower().strip()
