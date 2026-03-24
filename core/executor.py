"""
core/executor.py — Command execution.

Replace the mock execute() body with your real application dispatch logic.
The interface is intentionally simple: a single JSON-serialisable dict in.
"""
from __future__ import annotations
import json

from core.registry import CommandResult


def execute(result: CommandResult) -> None:
    """
    Mock executor — prints the structured JSON output.
    Replace this with your real application action dispatch.
    """
    payload = result.to_dict()
    payload["raw_transcript"] = result.raw_transcript

    print("\n" + "─" * 60)
    print("🎙  COMMAND RECOGNISED")
    print(json.dumps(payload, indent=2))
    print("─" * 60 + "\n")

    # Example of how your real dispatch might look:
    # for cmd in result.commands:
    #     your_app.dispatch(cmd.intent, cmd.parameters)
