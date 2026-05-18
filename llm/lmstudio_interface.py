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
from emulation.scope_states import ScopeInfo
from llm.prompts import SYSTEM_PROMPTS
from llm.utils import add_no_tool, format_actions, _NO_TOOL, get_schema_analysis, get_schema_no_analysis


# ── LM Studio implementation using lmstudio package ──────────────────────────

class LMStudioLLM:
    def __init__(self, model_name: str = "qwen3.5-2b", use_analysis = True, max_tool_calls = 3, min_confidence = 0.7) -> None:
        """
        Instantiate the LM Studio connection and load the given model.
        :param model_name: Which LLM to use for inference
        :param max_tool_calls: Maximum number of tools allowed to be triggered by one transcription
        :param min_confidence: Minimum confidence required to trigger a tool call
        """
        self.max_tool_calls = max_tool_calls
        self.min_confidence = min_confidence
        self.use_analysis = use_analysis
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

        self.system_prompt = SYSTEM_PROMPTS["has_analysis"] if self.use_analysis else SYSTEM_PROMPTS["no_analysis"]

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
        selected_tools = []
        tool_call = {'intent': "initial"}

        try:
            chat = lms.Chat(self.system_prompt)
            config = {
                "temperature": 0.0,
                "max_tokens": 256,
            }

            while tool_call['intent'] != _NO_TOOL.name:
                next_scope_info = next(available)
                next_available = add_no_tool(next_scope_info.actions)
                # When no actions are available, no use in running the model further
                if len(next_available) < 2:
                    return
                message =\
                    f"Transcript: \"{transcript}\"\nCurrent scope: {next_scope_info.name}, {next_scope_info.description}\nAvailable commands:\n{format_actions(next_available)}\n\nOutput JSON:" \
                    if len(selected_tools) == 0 else \
                    f"Already processed: {selected_tools}\nOriginal transcript: \"{transcript}\"\nCurrent scope: {next_scope_info.name}, {next_scope_info.description}\nAvailable commands:\n{format_actions(next_available)}\n\nOutput JSON:"
                chat.add_user_message(message)

                schema = get_schema_analysis(next_available) if self.use_analysis else get_schema_no_analysis(next_available)
                response = self._model.respond(
                    chat,
                    config=config,
                    response_format=schema,
                )
                chat.add_assistant_response(response)
                tool_call = response.parsed

                selected_tools.append(tool_call['intent'])
                yield ResolvedCommand(intent=tool_call['intent'], parameters=tool_call.get('parameters', {}), layer="llm", reasoning=tool_call.get('analysis', ''), confidence=tool_call.get('confidence', 1.0))
                if len(selected_tools) >= self.max_tool_calls:
                    if self.max_tool_calls > 1:
                        print(f"[Layer3] Maximum number of tools reached. Stopping execution.")
                    return


        except Exception as e:
            print(f"[Layer3] Error during LM Studio inference: {e}")
