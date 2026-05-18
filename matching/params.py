"""
matching/params.py — Extract typed parameters from transcripts.

Handles spoken numbers ("three", "twenty-five") and numeric digits.
Extend with more extractors as your commands gain new parameter types.
"""
from __future__ import annotations
import re
from typing import Any

from emulation.scope_states import Action

# Spoken number → int (extend as needed)
_WORD_TO_NUM: dict[str, int] = {
    "zero": 0, "one": 1, "first": 1, "two": 2, "second": 2, "seconds": 2, "too": 2,
    "three": 3, "third": 3, "four": 4, "fourth": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
}


def _word_number(text: str) -> int | None:
    """Try to parse one or two words as a spoken number."""
    text = text.lower().strip()
    if text in _WORD_TO_NUM:
        return _WORD_TO_NUM[text]
    parts = text.split()
    if len(parts) == 2 and parts[0] in _WORD_TO_NUM and parts[1] in _WORD_TO_NUM:
        return _WORD_TO_NUM[parts[0]] + _WORD_TO_NUM[parts[1]]
    return None


def extract_number(text: str, is_list: bool) -> int | list[int]:
    """Return the numbers found in text (digit or word form). If `is_list` is True, return a list of numbers, else, return the first one."""
    l = []
    # Digit first
    for m in re.finditer(r"\b(\d+)\b", text):
        if not is_list:
            return int(m.group(1))
        l.append(int(m.group(1)))
    # Word form — scan each 1–2 word window
    words = text.split()
    prev_candidate = ""
    for i in range(len(words)):
        for j in (1, 2):
            candidate = " ".join(words[i: i + j])
            # Avoid adding the same number twice
            if candidate == prev_candidate:
                continue
            prev_candidate = candidate
            n = _word_number(candidate)
            if n is not None:
                if not is_list:
                    return n
                l.append(n)
    return l


# ── Template matching ──────────────────────────────────────────────────────────

extractor_map = {
    "number": extract_number,
}


def extract_parameters(
    transcript: str,
    command: Action,
) -> dict[str, Any]:
    """
    Given a list of expected parameter names (from CommandDef.parameters),
    attempt to extract each from the transcript.

    Returns a dict with whatever was found (missing params are omitted).
    """
    result: dict[str, Any] = {}

    parameters = {}
    type_map = {"integer": "number", "number": "number", "string": "string"}
    for key, value in command.input_schema.get('properties', {}).items():
        value_type = value.get("type")
        if value_type == "array":
            sub_type = value.get("items", {}).get("type")
            parameters[key] = {"type": type_map.get(sub_type), "is_array": True}
        else:
            parameters[key] = {"type": type_map.get(value_type), "is_array": False}

    for param_name, param in parameters.items():
        param_type = param.get("type", "")
        extractor = extractor_map.get(param_type)
        if extractor is None:
            continue
        is_array = param.get("is_array", False)
        value = extractor(transcript, is_array)
        if value is not None:
            result[param_name] = value
    return result
