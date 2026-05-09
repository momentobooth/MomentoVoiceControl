import json
from typing import Any

from emulation.scope_states import Action, ScopeNames


def get_unique_schemas(available: list[Action]) -> list[dict[str, Any]]:
    schemas: list[str] = [json.dumps(tool.input_schema) for tool in available]
    unique_schemas = [json.loads(s) for s in set(schemas)]
    return unique_schemas


def get_schema_no_analysis(available: list[Action]) -> dict[str, Any]:
    intent_options: list[str] = [tool.name for tool in available]
    unique_schemas = get_unique_schemas(available)

    return {
        "type": "object",
        "properties": {
            "intent": {
                "enum": intent_options,
            },
            "parameters": {
                "anyOf": unique_schemas,
            },
        },
        "required": ["intent", "parameters"],
        "additionalProperties": False,
    }

def get_schema_analysis(available: list[Action]) -> dict[str, Any]:
    intent_options: list[str] = [tool.name for tool in available]
    unique_schemas = get_unique_schemas(available)

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
