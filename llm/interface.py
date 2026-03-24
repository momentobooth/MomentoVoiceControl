"""
llm/interface.py — LLM fallback for intent extraction.

Two implementations:
  MockLLM       — prints what it would do; useful during development.
  LlamaCppLLM   — real local LLM via llama-cpp-python.

Recommended model for CPU:
  Phi-3 Mini 3.8B Q4_K_M (~2.4 GB)  → fast, surprisingly capable at structured output
  Alternatively: Mistral 7B Q4_K_M  → more capable, ~4 GB, ~800 ms on i7

The prompt is structured so the LLM outputs JSON only — no prose.
We ask for the response in a constrained format and parse it safely.
"""
from __future__ import annotations
import json
import re

from core.registry import ResolvedCommand
from matching.params import extract_parameters


# ── Prompt template ───────────────────────────────────────────────────────────

_SYSTEM = """\
You are a voice command parser for a kiosk application.
Given a spoken transcript and a list of available commands, extract all commands 
that the user intended to trigger. Respond ONLY with valid JSON, no prose.

Output format:
{"commands": [{"intent": "<command_name>", "parameters": {"param": value}}]}

Rules:
- Only use command names from the provided list.
- If the transcript contains no commands, return {"commands": []}.
- Extract multiple commands if the user said several things (e.g. "select all and continue").
- For parameters, extract numeric values when present.
"""

def _build_prompt(transcript: str, available: list[dict]) -> str:
    cmds_json = json.dumps(available, indent=2)
    return (
        f"Available commands:\n{cmds_json}\n\n"
        f'Transcript: "{transcript}"\n\n'
        f"Output JSON:"
    )


# ── Mock implementation (no model needed) ─────────────────────────────────────

class MockLLM:
    """
    Simulates LLM behaviour without loading a model.
    Useful for development and testing the pipeline end-to-end.
    """

    def extract_intent(
        self, transcript: str, available: list[dict]
    ) -> list[ResolvedCommand]:
        print(f"[Layer3/Mock] Would call LLM with transcript: {transcript!r}")
        print(f"[Layer3/Mock] Available commands: {[c['name'] for c in available]}")
        # Return empty — simulates "no match found"
        return []


# ── Real llama.cpp implementation ─────────────────────────────────────────────

class LlamaCppLLM:
    """
    Local LLM via llama-cpp-python.

    Installation:
        pip install llama-cpp-python

    Model download (example — Phi-3 Mini, ~2.4 GB):
        huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf \
            Phi-3-mini-4k-instruct-q4.gguf --local-dir ./models

    Usage:
        llm = LlamaCppLLM("./models/Phi-3-mini-4k-instruct-q4.gguf")
    """

    def __init__(self, model_path: str, n_ctx: int = 2048) -> None:
        from llama_cpp import Llama
        print(f"[Layer3] Loading LLM from {model_path}…")
        self._llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=4,       # leave 4 for OS + VAD/STT threads
            verbose=False,
        )
        print("[Layer3] LLM ready.")

    def extract_intent(
        self, transcript: str, available: list[dict]
    ) -> list[ResolvedCommand]:
        prompt = _build_prompt(transcript, available)

        # Use chat completion format (most instruction-tuned models expect it)
        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=256,
            temperature=0.0,   # deterministic
            stop=["```"],
        )

        raw = response["choices"][0]["message"]["content"].strip()
        return self._parse_response(raw, available)

    def _parse_response(
        self, raw: str, available: list[dict]
    ) -> list[ResolvedCommand]:
        # Strip markdown fences if the model adds them despite instructions
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"[Layer3] Could not parse LLM output: {raw!r}")
            return []

        valid_names = {c["name"] for c in available}
        results: list[ResolvedCommand] = []

        for item in data.get("commands", []):
            intent = item.get("intent", "")
            if intent not in valid_names:
                continue   # hallucinated command — discard

            # Use LLM-extracted params, then fill any missing ones with regex
            cmd_def = next(c for c in available if c["name"] == intent)
            llm_params = item.get("parameters", {})
            regex_params = extract_parameters(
                raw, cmd_def.get("parameters", [])
            )
            merged = {**regex_params, **llm_params}   # LLM wins on conflicts

            results.append(
                ResolvedCommand(intent=intent, parameters=merged, confidence=0.85)
            )

        print(f"[Layer3] LLM extracted {len(results)} command(s).")
        return results
