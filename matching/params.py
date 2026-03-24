"""
matching/params.py — Extract typed parameters from transcripts.

Handles spoken numbers ("three", "twenty-five") and numeric digits.
Extend with more extractors as your commands gain new parameter types.
"""
from __future__ import annotations
import re
from typing import Any

# Spoken number → int (extend as needed)
_WORD_TO_NUM: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
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


def extract_number(text: str) -> int | None:
    """Return the first number found in text (digit or word form)."""
    # Digit first
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return int(m.group(1))
    # Word form — scan each 1–2 word window
    words = text.split()
    for i in range(len(words)):
        for j in (1, 2):
            candidate = " ".join(words[i: i + j])
            n = _word_number(candidate)
            if n is not None:
                return n
    return None


# ── Template matching ──────────────────────────────────────────────────────────

_EXTRACTORS = {
    "count": extract_number,
    "number": extract_number,
    "amount": extract_number,
    "quantity": extract_number,
}


def extract_parameters(
    transcript: str,
    parameter_names: list[str],
) -> dict[str, Any]:
    """
    Given a list of expected parameter names (from CommandDef.parameters),
    attempt to extract each from the transcript.

    Returns a dict with whatever was found (missing params are omitted).
    """
    result: dict[str, Any] = {}
    for param in parameter_names:
        extractor = _EXTRACTORS.get(param)
        if extractor is None:
            continue
        value = extractor(transcript)
        if value is not None:
            result[param] = value
    return result
