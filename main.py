"""
main.py — Entry point for the voice control service.

> note
> Initially vibe-coded with Claude

Run:
    python main.py

Swap MockLLM for LlamaCppLLM when you have a model downloaded:
    llm = LlamaCppLLM("./models/Phi-3-mini-4k-instruct-q4.gguf")
"""
import queue
import signal
import sys
import time

from audio.vad_loop import VADLoop
from core.pipeline import VoiceControlPipeline
from core.registry import CommandRegistry
from llm.interface import MockLLM  # swap to LlamaCppLLM when ready


def main():
    # ── Shared state ──────────────────────────────────────────────────────────
    utterance_queue: queue.Queue = queue.Queue(maxsize=8)
    registry = CommandRegistry()

    # ── Inject initial screen commands ────────────────────────────────────────
    registry.update_commands({
        "screen": "MainMenu",
        "commands": [
            {
                "name": "go_back",
                "examples": ["go back", "back", "previous", "return"],
            },
            {
                "name": "select_all",
                "examples": ["select all", "select everything"],
            },
            {
                "name": "continue",
                "examples": ["continue", "next", "proceed", "go ahead"],
            },
            {
                "name": "print",
                "parameters": ["count"],
                "examples": [
                    "print",
                    "print it",
                    "print {count}",
                    "print {count} times",
                    "print {count} copies",
                ],
            },
        ],
    })

    # ── Build pipeline ────────────────────────────────────────────────────────
    llm = MockLLM()
    pipeline = VoiceControlPipeline(registry, llm, utterance_queue)
    vad = VADLoop(utterance_queue)

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    def handle_exit(sig, frame):
        print("\n[Main] Shutting down…")
        vad.stop()
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # ── Start ─────────────────────────────────────────────────────────────────
    pipeline.start()
    vad.start()

    print("\n[Main] Voice control running. Press Ctrl+C to stop.\n")

    # Simulate a screen change after 10 seconds
    # (in your app, call this whenever the screen changes)
    def simulate_screen_change():
        time.sleep(10)
        print("\n[Main] Simulating screen change → PrintScreen\n")
        registry.update_commands({
            "screen": "PrintScreen",
            "commands": [
                {
                    "name": "confirm_print",
                    "examples": ["confirm", "yes", "print now"],
                },
                {
                    "name": "cancel",
                    "examples": ["cancel", "no", "stop", "abort"],
                },
                {
                    "name": "set_copies",
                    "parameters": ["count"],
                    "examples": [
                        "set copies to {count}",
                        "{count} copies",
                        "change to {count}",
                    ],
                },
            ],
        })

    import threading
    threading.Thread(target=simulate_screen_change, daemon=True).start()

    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
