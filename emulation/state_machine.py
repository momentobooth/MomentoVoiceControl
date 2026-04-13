import json
from dataclasses import dataclass
from typing import Any

from scope_states import ScopeNames, SCOPE_STATES

@dataclass
class ScopeInfo:
    name: str
    tools: list[dict[str, Any]]


class StateMachine:
    """
    Represents a state machine for emulating MomentoBooth's state, allowing tool calls resulting in state transitions.

    :ivar state_name: The current state identifier.
    :type state_name: ScopeNames
    :ivar state: The current state's configuration, including tools and transitions.
    :type state: dict
    """

    states = SCOPE_STATES

    def __init__(self, start_state: ScopeNames = ScopeNames.START_SCREEN):
        self.state_name = start_state
        self.state = self.states[start_state]
        self.call_history = []

    def get_tools(self):
        return [
            {
                "name": tool['name'],
                "title": tool['title'],
                "description": tool['description'],
                "examples": tool['examples'],
                "inputSchema": json.loads(tool['inputSchema']),
            }
            for tool in self.state
        ]

    def get_scope_info(self):
        return ScopeInfo(self.state_name.value, self.get_tools())

    def get_current_scope(self):
        return self.state_name.value

    def execute(self, tool: str, arguments: dict):
        tools = {t['name']: t for t in self.state}
        tool_def = tools[tool]
        next_state_name: ScopeNames = tool_def.get('next_state', self.state_name)
        print(f"[State machine] Executing tool: {tool} with arguments: {arguments} in scope {self.state_name}, navigating to {next_state_name.value}")
        self.call_history.append({"tool": tool, "arguments": arguments})
        self.state_name = next_state_name
        self.state = self.states[next_state_name]
