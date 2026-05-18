"""
matching/resolver.py — Three-layer command resolution.

Layer 1 — Fuzzy matching (rapidfuzz)
  Fast, < 1 ms.  Strong match (score ≥ FUZZY_THRESHOLD) → done.

Layer 2 — Embedding similarity (sentence-transformers)
  ~20–50 ms per query with all-MiniLM-L6-v2.
  Falls back to Layer 3 only if cosine similarity is low.

Layer 3 — LLM intent extraction (llama.cpp)
  Slowest, used only when Layers 1–2 fail.
  Also handles multi-command sentences.
"""
from __future__ import annotations
import json
import re
from typing import Any

import numpy as np
from rapidfuzz import fuzz, process as rfprocess

from core.registry import CommandDef, CommandRegistry, ResolvedCommand
from emulation.scope_states import ScopeInfo
from llm.interface import LLMInterface
from matching.params import extract_parameters

# ── Thresholds ─────────────────────────────────────────────────────────────────
FUZZY_THRESHOLD = 82         # 0–100; above this → immediate execute
EMBED_THRESHOLD = 0.72       # cosine similarity; above this → execute
EMBED_MODEL = "all-MiniLM-L6-v2"


class CommandResolver:
    """
    Initialise once; call resolve(transcript) per utterance.
    Stays in sync with the registry via on_update callback.
    """

    def __init__(self, registry: CommandRegistry, llm_interface: LLMInterface) -> None:
        self._registry = registry
        self._llm = llm_interface

        # Lazy-load embedding model (only if Layer 2 is actually needed)
        self._embed_model = None
        self._load_embed_model()
        self._embed_index: list[tuple[np.ndarray, CommandDef]] = []   # (vector, cmd)

        registry.on_update(self._rebuild_index)
        if registry.commands:
            self._rebuild_index(registry)

    # ── Public ────────────────────────────────────────────────────────────────

    def resolve(self, transcript: str) -> list[ResolvedCommand]:
        """
        Returns a (possibly empty) list of ResolvedCommand.
        Empty list → treat as non-command speech, discard.
        """
        transcript = transcript.strip().lower()
        if not transcript or not self._registry.commands:
            return []

        # Layer 1
        result = self._fuzzy_match(transcript)
        if result:
            return result

        # Layer 2
        result = self._embed_match(transcript)
        if result:
            return result

        # Layer 3
        return self._llm_match(transcript)

    # ── Layer 1: Fuzzy ────────────────────────────────────────────────────────

    def _fuzzy_match(self, transcript: str) -> list[ResolvedCommand]:
        pairs = self._registry.all_example_pairs()
        if not pairs:
            return []

        examples = [p[0] for p in pairs]
        match = rfprocess.extractOne(
            transcript,
            examples,
            scorer=fuzz.WRatio,   # handles word order variation
        )
        if not match:
            return []

        best_text, score, idx = match
        if score < FUZZY_THRESHOLD:
            return []

        cmd = pairs[idx][1]
        params = extract_parameters(transcript, cmd)
        print(f"[Layer1] fuzzy score={score:.0f} → {cmd.name}")
        return [ResolvedCommand(intent=cmd.name, parameters=params,
                                confidence=score / 100, layer="fuzzy")]

    # ── Layer 2: Embeddings ───────────────────────────────────────────────────

    def _load_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            print("[Layer2] Loading embedding model…")
            self._embed_model = SentenceTransformer(EMBED_MODEL)
            print("[Layer2] Embedding model ready.")

    def _rebuild_index(self, registry: CommandRegistry) -> None:
        """Re-encode all command examples whenever commands change."""
        if self._embed_model is None:
            # Defer until first embed lookup is actually needed
            self._embed_index = []
            return
        pairs = registry.all_example_pairs()
        texts = [p[0] for p in pairs]
        if not texts:
            self._embed_index = []
            return
        vectors = self._embed_model.encode(texts, normalize_embeddings=True)
        self._embed_index = list(zip(vectors, [p[1] for p in pairs]))
        print(f"[Layer2] Index rebuilt: {len(texts)} examples.")

    def _embed_match(self, transcript: str) -> list[ResolvedCommand]:
        self._load_embed_model()

        # Build index if not yet done (first time embeddings are needed)
        if not self._embed_index:
            self._rebuild_index(self._registry)
        if not self._embed_index:
            return []

        query_vec = self._embed_model.encode(
            [transcript], normalize_embeddings=True
        )[0]

        best_score = -1.0
        best_cmd: CommandDef | None = None
        for vec, cmd in self._embed_index:
            score = float(np.dot(query_vec, vec))
            if score > best_score:
                best_score = score
                best_cmd = cmd

        if best_score < EMBED_THRESHOLD or best_cmd is None:
            print(f"[Layer2] embed score={best_score:.3f} — below threshold.")
            return []

        params = extract_parameters(transcript, best_cmd)
        print(f"[Layer2] embed score={best_score:.3f} → {best_cmd.name}")
        return [ResolvedCommand(intent=best_cmd.name, parameters=params,
                                confidence=best_score, layer="embedding")]

    # ── Layer 3: LLM ─────────────────────────────────────────────────────────

    def _llm_match(self, transcript: str) -> list[ResolvedCommand]:
        def scope_info_generator():
            while True:
                next_state_tools = ScopeInfo(
                    name=self._registry.screen,
                    actions=self._registry.commands,
                    description=''
                )
                yield next_state_tools
        # Todo allow multi-turn interactions, but execute commands when available.
        results_generator = self._llm.extract_intent(transcript, scope_info_generator())
        results = next(results_generator)
        return [results]
