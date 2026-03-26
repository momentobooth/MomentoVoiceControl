"""
core/pipeline.py — STT + matching worker loop.

Architecture
------------
  VADLoop  ──[audio queue]──▶  Pipeline._worker_thread
                                    │
                                    ▼
                              Transcriber.transcribe()
                                    │
                                    ▼
                              CommandResolver.resolve()
                                    │
                            ┌───────┴────────┐
                         commands          empty
                            │                │
                         execute()        discard
"""
from __future__ import annotations
import queue
import threading
import time

import numpy as np

from core.executor import execute
from core.registry import CommandRegistry, CommandResult
from stt.transcriber import Transcriber
from matching.resolver import CommandResolver


class VoiceControlPipeline:
    """
    Ties together STT and command resolution in a single background thread.

    Parameters
    ----------
    registry        : shared CommandRegistry (updated by the MQTT bridge)
    llm_interface   : MockLLM or LlamaCppLLM
    utterance_queue : audio chunks from VADLoop
    bridge          : MQTTBridge used to dispatch resolved commands
    """

    def __init__(
        self,
        registry: CommandRegistry,
        llm_interface,
        utterance_queue: queue.Queue,
        bridge,
    ) -> None:
        self._registry = registry
        self._q = utterance_queue
        self._bridge = bridge
        self._transcriber = Transcriber()
        self._resolver = CommandResolver(registry, llm_interface)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Keep hotwords in sync with the registry automatically
        registry.on_update(self._transcriber.update_hotwords)
        if registry.commands:
            self._transcriber.update_hotwords(registry)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[Pipeline] Worker started.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                audio: np.ndarray = self._q.get(timeout=0.5)
            except queue.Empty:
                continue

            t0 = time.perf_counter()

            # 1. Transcribe
            transcript = self._transcriber.transcribe(audio)
            if not transcript:
                print("[Pipeline] No speech detected, skipping.")
                continue

            t1 = time.perf_counter()
            print(f"[Pipeline] Transcript ({(t1-t0)*1000:.0f} ms): {transcript!r}")

            # 2. Resolve commands
            commands = self._resolver.resolve(transcript)

            t2 = time.perf_counter()
            print(f"[Pipeline] Resolution ({(t2-t1)*1000:.0f} ms): "
                  f"{[c.intent for c in commands] or 'no match'}")

            if not commands:
                continue

            # 3. Execute
            result = CommandResult(commands=commands, raw_transcript=transcript)
            execute(result, self._bridge)

            total_ms = (time.perf_counter() - t0) * 1000
            print(f"[Pipeline] Total latency: {total_ms:.0f} ms")
