"""
tests/test_matching.py — Tests for command resolution layers.

Run without microphone or GPU:
    python -m pytest tests/ -v
"""
import pytest
from unittest.mock import MagicMock

from core.registry import CommandRegistry, CommandDef
from matching.params import extract_number, extract_parameters
from matching.resolver import CommandResolver


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def registry():
    reg = CommandRegistry()
    reg.update_commands({
        "screen": "TestScreen",
        "commands": [
            {"name": "go_back",     "examples": ["go back", "back", "previous"]},
            {"name": "continue",    "examples": ["continue", "next", "proceed"]},
            {"name": "select_all",  "examples": ["select all", "select everything"]},
            {
                "name": "print",
                "parameters": ["count"],
                "examples": ["print", "print {count}", "print {count} copies"],
            },
        ],
    })
    return reg


@pytest.fixture
def resolver(registry):
    mock_llm = MagicMock()
    mock_llm.extract_intent.return_value = []
    return CommandResolver(registry, mock_llm)


# ── Parameter extraction ──────────────────────────────────────────────────────

class TestNumberExtraction:
    def test_digit(self):
        assert extract_number("print 5 copies") == 5

    def test_word(self):
        assert extract_number("print three copies") == 3

    def test_compound(self):
        assert extract_number("twenty five") == 25

    def test_none(self):
        assert extract_number("go back") is None

    def test_extract_parameters_count(self):
        result = extract_parameters("print 7 times", ["count"])
        assert result == {"count": 7}

    def test_extract_parameters_word_count(self):
        result = extract_parameters("print five times", ["count"])
        assert result == {"count": 5}


# ── Fuzzy matching ────────────────────────────────────────────────────────────

class TestFuzzyMatching:
    def test_exact_match(self, resolver):
        results = resolver.resolve("go back")
        assert len(results) == 1
        assert results[0].intent == "go_back"
        assert results[0].layer == "fuzzy"

    def test_partial_match(self, resolver):
        results = resolver.resolve("go back please")
        assert len(results) == 1
        assert results[0].intent == "go_back"

    def test_typo_tolerance(self, resolver):
        # "contunue" — one char off
        results = resolver.resolve("contunue")
        assert len(results) == 1
        assert results[0].intent == "continue"

    def test_no_command_speech(self, resolver):
        # Casual speech should not match
        results = resolver.resolve("what a beautiful day today")
        assert results == []

    def test_print_with_count(self, resolver):
        results = resolver.resolve("print 3 copies")
        assert len(results) == 1
        assert results[0].intent == "print"
        assert results[0].parameters.get("count") == 3

    def test_print_word_count(self, resolver):
        results = resolver.resolve("print five")
        assert len(results) == 1
        assert results[0].intent == "print"
        assert results[0].parameters.get("count") == 5


# ── Registry update ───────────────────────────────────────────────────────────

class TestRegistryDynamism:
    def test_commands_update(self, resolver, registry):
        registry.update_commands({
            "screen": "NewScreen",
            "commands": [
                {"name": "confirm", "examples": ["confirm", "yes"]},
            ],
        })
        results = resolver.resolve("yes")
        assert len(results) == 1
        assert results[0].intent == "confirm"

    def test_old_commands_gone(self, resolver, registry):
        registry.update_commands({
            "screen": "NewScreen",
            "commands": [
                {"name": "confirm", "examples": ["confirm", "yes"]},
            ],
        })
        # "go back" was on the old screen — should not match now
        results = resolver.resolve("go back")
        assert results == []
