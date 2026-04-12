"""
llm/lmstudio_interface.py — LLM fallback for intent extraction using lmstudio package.

This implementation uses the lmstudio Python package to provide local LLM capabilities
with enforced structured output and proper response handling.
"""

from __future__ import annotations
import json
from typing import Any, Generator

import lmstudio as lms

from core.registry import ResolvedCommand

def get_schema(available: list[dict]) -> dict[str, Any]:
    intent_options: list[str] = [tool['name'] for tool in available]
    return {
        "type": "object",
        "properties": {
            "intent": {
                "enum": intent_options,
            },
            "parameters": {
                "type": "object",
            },
        },
        "required": ["intent", "parameters"],
        "additionalProperties": False,
    }

_NO_TOOL = {
    "name": "do_nothing_and_finish",
    "title": "Do Nothing and Finish",
    "description": "Ends command execution",
    "inputSchema": { "type": "object", "additionalProperties": False }
}

# ── Prompt template ───────────────────────────────────────────────────────────

_SYSTEM = """\
You are a voice command parser for a kiosk application.
Given a spoken transcript and a list of available commands, extract all commands 
that the user intended to trigger. Respond ONLY with valid JSON, no prose.

Output format:
{"intent": "<command_name>", "parameters": {"param": value}}

Rules:
- Only use command names from the provided list.
- If the transcript contains no commands, return {"intent": "do_nothing_and_finish", "parameters": {}}.
- Extract multiple commands if the user said several things (e.g. "select all and continue").
- In case there are multiple commands, you will execute one command at a time, and then be presented with the new commands available after the command is executed.
- For parameters, extract numeric values when present.
"""

def add_no_tool(initial_list: list[dict]) -> list[dict]:
    return [_NO_TOOL] + list(initial_list)


def _build_prompt(transcript: str, available: list[dict]) -> str:
    cmds_json = json.dumps(available, indent=2)
    return (
        f"Available commands:\n{cmds_json}\n\n"
        f'Transcript: "{transcript}"\n\n'
        f"Output JSON:"
    )


# ── LM Studio implementation using lmstudio package ──────────────────────────

class LMStudioLLM:
    def __init__(self, model_name: str = "qwen3.5-2b", max_tool_calls = 3) -> None:
        """
        Instantiate the LM Studio connection and load the given model.
        :param model_name: Which LLM to use for inference
        """
        self.max_tool_calls = max_tool_calls
        try:
            self._model_name = model_name
            print(f"[Layer3] Loading LM Studio model {model_name}...")

            # Initialize with structured output enforcement
            self._client = lms.Client('localhost:1234')
            self._model = self._client.llm.model(self._model_name)

            print("[Layer3] LM Studio model ready.")
        except ImportError:
            raise ImportError("The lmstudio package is required. Install with: pip install lmstudio")
        except Exception as e:
            print(f"[Layer3] Error initializing LM Studio: {e}")
            raise

    def extract_intent(
            self, transcript: str, available: Generator[list[dict]]
    ) -> Generator[ResolvedCommand]:
        """
        Extracts the actions that the user intends to trigger based on the transcript of their speech.
        The function expects `available` is a generator of available commands that will be updated as the yielded `ResolvedCommand` objects are consumed.

        :param transcript: transcript to be analyzed
        :param available: generator supplying currently available commands
        :return:
        """
        first_available = add_no_tool(next(available))
        prompt = _build_prompt(transcript, first_available)
        tool_calls = 0

        try:
            # Use chat completion with structured output enforcement
            chat = lms.Chat(_SYSTEM)
            chat.add_user_message(prompt)
            config = {
                "temperature": 0.0,
                "max_tokens": 256,
            }
            response = self._model.respond(
                chat,
                config=config,
                response_format=get_schema(first_available),
            )

            tool_call = response.parsed
            while tool_call['intent'] != _NO_TOOL['name']:
                tool_calls = tool_calls + 1
                yield ResolvedCommand(intent=tool_call['intent'], parameters=tool_call.get('parameters', {}), layer="llm")
                if tool_calls >= self.max_tool_calls:
                    print(f"[Layer3] Maximum number of tools reached. Stopping execution.")
                    return
                next_available = add_no_tool(next(available))
                chat.add_user_message(f"Available commands:\n{next_available}\n\nOutput JSON:")

                response = self._model.respond(
                    chat,
                    config=config,
                    response_format=get_schema(next_available),
                )
                tool_call = response.parsed


        except Exception as e:
            print(f"[Layer3] Error during LM Studio inference: {e}")
