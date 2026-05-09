"""
llm/lmstudio_interface.py — LLM fallback for intent extraction using lmstudio package.

This implementation uses the lmstudio Python package to provide local LLM capabilities
with enforced structured output and proper response handling.
"""

from __future__ import annotations
import json
from typing import Any, Generator, Set

import lmstudio as lms

from core.registry import ResolvedCommand
from emulation.scope_states import Action, ScopeInfo, ScopeNames


def get_schema(available: list[Action]) -> dict[str, Any]:
    intent_options: list[str] = [tool.name for tool in available]
    schemas: list[str] = [json.dumps(tool.input_schema) for tool in available]
    unique_schemas = [json.loads(s) for s in set(schemas)]

    return {
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
                "minLength": 1,
                # "maxLength": 1000
            },
            "intent": {
                "enum": intent_options,
            },
            "parameters": {
                "anyOf": unique_schemas,
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            }
        },
        "required": ["analysis", "intent", "parameters", "confidence"],
        "additionalProperties": False,
    }

_NO_TOOL = Action(
    name="do_nothing_and_finish",
    title="Do Nothing and Finish",
    description="Ends command execution. Use this if all words in the transcript have already been executed or if no further commands are explicitly mentioned.",
    input_schema={"type": "object", "additionalProperties": False},
    examples=[],
    next_state=ScopeNames.START_SCREEN,  # Not actually used
)

# ── Prompt template ───────────────────────────────────────────────────────────

_SYSTEM = """\
## Role
You are a voice command controller for a photo kiosk. Your task is to process a transcript by extracting ONE command at a time that matches the user's intent and the currently available commands.

## Process Logic
1. **Analyze:** Examine the full transcript and the list of available commands.
2. **Reason:** Determine which part of the transcript hasn't been executed yet and which command matches that intent.
3. **Select:** Pick the single most appropriate command.
4. **Completion:** If all user requests in the transcript are fulfilled, or if the transcript contains no relevant commands, use 'do_nothing_and_finish'.

## Rules
- **Literal Extraction Only:** You are a passive parser. Your only source of truth is the 'Original transcript'. If every word in the transcript has been accounted for by the 'Executed' list, you MUST return 'do_nothing_and_finish'.
- **One at a time:** Respond with exactly one JSON object per turn.
- **State Awareness:** You are part of a loop. After you emit a command, the system executes it and calls you again with the updated state and the same transcript. 
- **Sequential Execution:** If a transcript contains multiple steps (e.g., "Take a photo and then open the gallery"), extract the first logical step first.
- **No Prediction:** Do NOT suggest or predict the next logical step. Only extract commands that are explicitly requested in the provided transcript.
- **Exhaustion:** If the transcript was "Start" and you already emitted the "start" command, the transcript is now exhausted. Your only valid response is 'do_nothing_and_finish'.

## Output Format
You must respond with a JSON object following this structure:
{
  "analysis": "Identify which words from the transcript are NOT yet in the 'Executed' list. Then, briefly explain why this command was chosen based on the transcript and history.",
  "intent": "command_name",
  "parameters": { parameters according to the command's parameters_format },
  "confidence": 0.0-1.0
}
"""

def add_no_tool(initial_list: list[Action]) -> list[Action]:
    return list(initial_list) + [_NO_TOOL]


def format_actions(actions: list[Action]) -> str:
    mapped_actions = []
    for a in actions:
        has_params = a.input_schema_description != "{}"
        examples_mapped = [
            ex.phrase if not has_params else ex.to_dict()
            for ex in a.examples
        ]
        mapped = {
            "name": a.name,
            "title": a.title,
            "description": f"{a.description}",
            "parameters_format": a.input_schema_description if has_params else "This tool takes no parameters.",
            "examples": examples_mapped,
        }
        mapped_actions.append(mapped)
    return json.dumps(mapped_actions, indent=2)


# ── LM Studio implementation using lmstudio package ──────────────────────────

class LMStudioLLM:
    def __init__(self, model_name: str = "qwen3.5-2b", max_tool_calls = 3, min_confidence = 0.7) -> None:
        """
        Instantiate the LM Studio connection and load the given model.
        :param model_name: Which LLM to use for inference
        :param max_tool_calls: Maximum number of tools allowed to be triggered by one transcription
        :param min_confidence: Minimum confidence required to trigger a tool call
        """
        self.max_tool_calls = max_tool_calls
        self.min_confidence = min_confidence
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
            self, transcript: str, available: Generator[ScopeInfo]
    ) -> Generator[ResolvedCommand]:
        """
        Extracts the actions that the user intends to trigger based on the transcript of their speech.
        The function expects `available` is a generator of available commands that will be updated as the yielded `ResolvedCommand` objects are consumed.

        :param transcript: transcript to be analyzed
        :param available: generator supplying currently available commands
        :return:
        """
        first_scope_info = next(available)
        first_available = add_no_tool(first_scope_info.actions)
        selected_tools = []

        try:
            chat = lms.Chat(_SYSTEM)
            chat.add_user_message(
                f"Already processed: {selected_tools}\nTranscript: \"{transcript}\"\nCurrent scope: {first_scope_info.name}\nAvailable commands:\n{format_actions(first_available)}\n\nOutput JSON:"
            )
            config = {
                "temperature": 0.0,
                "max_tokens": 256,
            }
            # Use chat completion with structured output enforcement
            response = self._model.respond(
                chat,
                config=config,
                response_format=get_schema(first_available),
            )
            chat.add_assistant_response(response)

            tool_call = response.parsed
            while tool_call['intent'] != _NO_TOOL.name:
                selected_tools.append(tool_call['intent'])
                if tool_call['confidence'] < self.min_confidence:
                    print(f"[Layer3] LLM reported an insufficient confidence of {tool_call['confidence']} for {tool_call['intent']}")
                yield ResolvedCommand(intent=tool_call['intent'], parameters=tool_call.get('parameters', {}), layer="llm", confidence=tool_call['confidence'], reasoning=tool_call['analysis'])
                if len(selected_tools) >= self.max_tool_calls:
                    print(f"[Layer3] Maximum number of tools reached. Stopping execution.")
                    return
                next_scope_info = next(available)
                next_available = add_no_tool(next_scope_info.actions)
                # When no actions are available, no use in running the model further
                if len(next_available) < 2:
                    return
                chat.add_user_message(
                    f"Already processed: {selected_tools}\nOriginal transcript: \"{transcript}\"\nCurrent scope: {next_scope_info.name}\nAvailable commands:\n{format_actions(next_available)}\n\nOutput JSON:"
                )

                response = self._model.respond(
                    chat,
                    config=config,
                    response_format=get_schema(next_available),
                )
                chat.add_assistant_response(response)
                tool_call = response.parsed


        except Exception as e:
            print(f"[Layer3] Error during LM Studio inference: {e}")
