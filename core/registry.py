"""
core/registry.py — Dynamic command registry.

The application calls update_commands() whenever the screen changes.
The registry keeps all three matchers in sync automatically.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandDef:
    name: str
    examples: list[str]
    parameters: list[str] = field(default_factory=list)

    def expanded_examples(self) -> list[str]:
        """Return examples with parameter slots replaced by regex-friendly tokens.

        E.g. "print {count} times" → "print <count> times"
        (used for display/embedding; actual extraction uses the raw template)
        """
        return [re.sub(r"\{(\w+)\}", r"<\1>", ex) for ex in self.examples]


@dataclass
class ResolvedCommand:
    intent: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    layer: str = "unknown"   # "fuzzy" | "embedding" | "llm"


@dataclass
class CommandResult:
    commands: list[ResolvedCommand]
    raw_transcript: str

    def to_dict(self) -> dict:
        return {
            "commands": [
                {
                    "intent": c.intent,
                    "parameters": c.parameters,
                    "confidence": round(c.confidence, 3),
                    "layer": c.layer,
                }
                for c in self.commands
            ]
        }


class CommandRegistry:
    """
    Central store of active commands.  Thread-safe for reads after update.

    Update from the application:
        registry.update_commands({
            "screen": "MainMenu",
            "commands": [
                {"name": "go_back", "examples": ["go back", "back"]},
                {"name": "print", "parameters": ["count"],
                 "examples": ["print", "print {count}", "print {count} times"]},
            ]
        })
    """

    def __init__(self) -> None:
        self.screen: str = ""
        self.commands: list[CommandDef] = []
        self._on_update_callbacks: list = []

    def update_commands(self, payload: dict) -> None:
        self.screen = payload.get("screen", "")
        self.commands = [
            CommandDef(
                name=cmd["name"],
                examples=cmd.get("examples", []),
                parameters=cmd.get("parameters", []),
            )
            for cmd in payload.get("commands", [])
        ]
        for cb in self._on_update_callbacks:
            cb(self)
        print(f"[Registry] Screen={self.screen!r}, {len(self.commands)} commands loaded: {[f"{{ name: {c.name}, params: {c.parameters} }}" for c in self.commands]}.")

    def on_update(self, callback) -> None:
        """Register a callback(registry) called after every update_commands()."""
        self._on_update_callbacks.append(callback)

    def all_example_pairs(self) -> list[tuple[str, CommandDef]]:
        """All (example_text, command) pairs for indexing."""
        pairs = []
        for cmd in self.commands:
            for ex in cmd.examples:
                pairs.append((ex, cmd))
        return pairs
