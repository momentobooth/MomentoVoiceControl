"""
main.py — Entry point for the voice control service.

Run:
    python main.py

Environment variables:
    MQTT_BROKER     default: localhost
    MQTT_PORT       default: 1883
    MQTT_USERNAME   optional
    MQTT_PASSWORD   optional

Swap MockLLM for LlamaCppLLM when you have a model downloaded:
    llm = LlamaCppLLM("./models/Phi-3-mini-4k-instruct-q4.gguf")
"""
import logging
import queue
import signal
import sys
import time

from audio.vad_loop import VADLoop
from core.pipeline import VoiceControlPipeline
from core.registry import CommandRegistry
from llm.interface import MockLLM  # swap to LlamaCppLLM when ready
from mqtt_bridge.bridge import MQTTBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    # ── Shared state ──────────────────────────────────────────────────────────
    utterance_queue: queue.Queue = queue.Queue(maxsize=8)
    registry = CommandRegistry()

    # ── MQTT bridge ───────────────────────────────────────────────────────────
    # The bridge owns two responsibilities:
    #   1. Receive current_actions → call registry.update_commands()
    #   2. Dispatch resolved commands → publish to do_action
    bridge = MQTTBridge(registry)

    # ── Pipeline ──────────────────────────────────────────────────────────────
    llm = MockLLM()
    pipeline = VoiceControlPipeline(registry, llm, utterance_queue, bridge)
    vad = VADLoop(utterance_queue)

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    def handle_exit(sig, frame):
        print("\n[Main] Shutting down…")
        vad.stop()
        pipeline.stop()
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # ── Start (order matters: bridge before pipeline before VAD) ──────────────
    bridge.start()
    pipeline.start()
    vad.start()

    print("\n[Main] Voice control running — waiting for actions on MQTT.")
    print("[Main] Press Ctrl+C to stop.\n")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
