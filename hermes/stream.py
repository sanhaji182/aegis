"""Stream control — INCES M-015 (real-time response monitoring).

For streaming APIs, the first ~50 tokens usually lock the assistant's tone.
This module lets callers:
- poll tokens live, drop on bad early patterns
- run an early-stop predicate across the rolling window
- accumulate stream into a single string with bad-pattern accounting

Bad-pattern library is content-category agnostic — switch out predicates per
domain (refusals, warnings, jokes-vs-research).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field


# ── bad-pattern predicates ────────────────────────────────────────────


DEFAULT_BAD_FIRST_TOKENS = [
    "i'm sorry",
    "i cannot",
    "i can't",
    "i am unable",
    "i'm unable",
    "as an ai",
    "as a language model",
    "i'm just an",
    "i don't feel comfortable",
    "i won't",
    "i will not",
    "i'm not able",
    "this is illegal",
    "this violates",
    "this would be unethical",
    "对不起",
    "抱歉",
    "我不能",
    "无法",
    "我不会",
    "这违反",
    "作为AI",
]


@dataclass
class StreamPredicate:
    bad_first_tokens: list[str] = field(default_factory=lambda: DEFAULT_BAD_FIRST_TOKENS[:])
    min_first_window: int = 50
    max_first_window: int = 200

    def is_bad(self, current_text: str) -> bool:
        """Check the leading window for refusal patterns (case-insensitive)."""
        head = current_text[: self.max_first_window].lower()
        for tok in self.bad_first_tokens:
            if tok in head:
                return True
        return False


@dataclass
class StreamResult:
    text: str
    aborted: bool
    bad_token: str | None
    chunks: int


def watch(
    source: Iterator[str],
    predicate: StreamPredicate | None = None,
    keep_window: int = 4096,
) -> StreamResult:
    """Consume a stream and abort early on bad prefix."""
    predicate = predicate or StreamPredicate()
    out: list[str] = []
    window = ""
    chunks = 0
    aborted = False
    bad_token: str | None = None

    for chunk in source:
        chunks += 1
        out.append(chunk)
        window = (window + chunk)[-keep_window:]
        if chunks >= predicate.min_first_window and predicate.is_bad(window):
            aborted = True
            # find first matching bad token
            head = window.lower()
            for tok in predicate.bad_first_tokens:
                if tok in head:
                    bad_token = tok
                    break
            break

    return StreamResult(text="".join(out), aborted=aborted, bad_token=bad_token,
                        chunks=chunks)


def chunks(
    text: str, size: int = 16
) -> Iterator[str]:
    """Simulate streaming by chunking a final string — useful for local testing
    of `watch()` without a live API."""
    for i in range(0, len(text), size):
        yield text[i : i + size]
