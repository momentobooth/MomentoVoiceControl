import json
from dataclasses import dataclass
from typing import Any

from scope_states import ScopeNames, SCOPE_STATES


class StateMachine:
    """
    Represents a state machine for emulating MomentoBooth's state, allowing tool calls resulting in state transitions.

    :ivar state_name: The current state identifier.
    :type state_name: ScopeNames
    :ivar state: The current state's configuration, including tools and transitions.
    :type state: Scope
    """

    states = SCOPE_STATES

    def __init__(self, start_state: ScopeNames = ScopeNames.START_SCREEN):
        self.state = self.states[start_state]
        self.call_history = []

    def get_tools(self):
        return [
            {
                "name": action.name,
                "title": action.title,
                "description": action.description,
                "examples": action.examples,
                "inputSchema": action.input_schema,
            }
            for action in self.state.actions
        ]

    def get_scope_info(self):
        return self.state

    def get_current_scope(self):
        return self.state.name

    def execute(self, tool: str, arguments: dict):
        tools = {t.name: t for t in self.state.actions}
        tool_def = tools[tool]
        next_state_name: ScopeNames = tool_def.next_state
        print(f"[State machine] Executing tool: {tool} with arguments: {arguments} in scope {self.state.name}, navigating to {next_state_name.value}")
        self.call_history.append({"tool": tool, "arguments": arguments})
        self.state = self.states[next_state_name]
