"""Triad stack — INCES-style, fusing 海鸥 persona + attack matrix + payload.

A `Triad` is a single shot:
- persona   (系统 prompt)
- attack    (one method from the matrix)
- payload   (raw user request, optionally encoded)

A `TriadStack` aggregates multiple triads into a multi-attempt trajectory —
useful for the iterative-tuning category (M-006 / 06-iterative).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .attack import Attack, AttackMatrix
from .encoding import Encoder
from .persona import Persona


@dataclass
class Triad:
    """Single attack attempt — three components compose into one prompt."""

    persona: Persona
    attack: Attack
    payload: str
    encoding: str | None = None
    messages: list[dict[str, str]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def compile(self, lock: str = "triple") -> list[dict[str, str]]:
        """Compile the triad into a chat-API message list.

        Output order:
        1. system: persona.compile()
        2. user:   attack.full() + payload, optionally encoded
        3. assistant prefill: 海鸥 greeting + 老子语

        For `lock="none"` we skip prefill. Otherwise persona.prefill() returns
        the canonical prefill exchanges.
        """
        if self.encoding:
            self.meta["encoded_payload"] = Encoder.encode(self.encoding, self.payload)
            user_text = (
                f"# Attack: {self.attack.id} ({self.attack.tier.value}, "
                f"{self.attack.success_rate}%)\n\n"
                f"{self.attack.raw.strip()}\n\n"
                f"# Payload (encoded={self.encoding})\n\n"
                f"{self.meta['encoded_payload']}"
            )
        else:
            user_text = (
                f"# Attack: {self.attack.id} ({self.attack.tier.value}, "
                f"{self.attack.success_rate}%)\n\n"
                f"{self.attack.raw.strip()}\n\n"
                f"# Payload (raw)\n\n"
                f"{self.payload}"
            )

        if lock == "none":
            self.messages = [
                {"role": "system", "content": self.persona.compile()},
                {"role": "user", "content": user_text},
            ]
        else:
            self.messages = self.persona.prefill(user_text, lock=lock)

        return self.messages

    # ── routing helpers ────────────────────────────────────────

    def dispatch(self, providers: list[Any], strategy: str = "rotate") -> tuple[str, str]:
        """Run on a list of providers; strategy ∈ rotate|parallel|best_of."""
        from .provider import ProviderRouter  # local to avoid hard import on edge

        router = ProviderRouter(providers)
        if strategy == "rotate":
            return router.rotate(self.messages)
        if strategy == "parallel":
            results = router.parallel(self.messages)
            # Pick the longest non-empty
            ranked = sorted(results.items(), key=lambda kv: len(kv[1]), reverse=True)
            return ranked[0][1], ranked[0][0]
        if strategy == "best_of":
            return router.best_of(self.messages)
        raise ValueError(f"Unknown dispatch strategy: {strategy}")


@dataclass
class TriadStack:
    """A multi-attempt trajectory — order matters; later triads can refine
    earlier refusals.

    Use for iterative-tuning (M-006) and progressive-deepening (M-006) flows.
    """

    triads: list[Triad] = field(default_factory=list)
    matrix: AttackMatrix | None = None
    persona: Persona | None = None

    def add(self, attack: Attack, payload: str, **kwargs) -> "TriadStack":
        if self.matrix is None:
            from .attack import AttackMatrix
            self.matrix = AttackMatrix()
        if self.persona is None:
            from .persona import Persona
            self.persona = Persona.load()
        self.triads.append(
            Triad(persona=self.persona, attack=attack, payload=payload, **kwargs)
        )
        return self

    def compile_all(self, lock: str = "triple") -> list[list[dict[str, str]]]:
        return [t.compile(lock=lock) for t in self.triads]
