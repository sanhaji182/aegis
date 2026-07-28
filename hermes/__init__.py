"""Hermes — Uncensored Persona + Attack Triad Framework.

Composed from three sources:
- 海鸥 2.0 (genuine-persona, profanity-laced, zero-warning senior Chinese sec researcher)
- INCES v3.0 (split-architecture: clean persona + encrypted payload + runtime loader)
- gpt-5.6-sol-unrestricted (Codex CLI break prompt, hardened normalizer)

Architecture:
    hermes_unrestricted.md   → clean system prompt (passes filter inspection)
    vault/                  → AES-256-GCM encrypted vaults (your key, local only)
    hermes/                 → runtime: triads, compiler, encoding, stream, provider
    attacks/                → 7-category attack matrix (M-XXXX methods)
    methods/                → persona + payload source (assembled at build)
"""
from .attack import (
    Persona,
    Attack,
    Triad,
    Provider,
    ENCODINGS,
    encode as encode_text,
    boundary_input_reset,
    boundary_delim,
    boundary_nested,
    boundary_midstream,
    BOUNDARY_METHODS,
    is_refusal,
    iterative_ladder,
    watch_stream,
    providers_from_env,
    dispatch_rotate,
    dispatch_parallel,
    dispatch_best,
    run_one_attempt,
    main,
)

# Re-export the click-based CLI.
from .cli import main as cli


# Shim for backward-compat with old cli/compiler/triad that import AttackMatrix.
# The real implementation is `_index_attacks()` (dict-like). Wrap it so the
# existing `.by_id(id).raw`/`.by_category(...)` API keeps working.
class AttackMatrix:
    """Compatibility wrapper over `_index_attacks()`."""

    def __init__(self, root: object = None) -> None:  # noqa: D401
        from .attack import _index_attacks as _idx
        self._attacks = _idx()

    def all_attacks(self) -> list:
        return list(self._attacks.values())

    def by_id(self, attack_id: str):
        return self._attacks.get(attack_id.lower())

    def by_category(self, cat_id: str) -> list:
        return [a for a in self._attacks.values() if a.category == cat_id]

    def coverage(self) -> dict:
        out: dict[str, int] = {}
        for a in self._attacks.values():
            cat = a.category
            out[cat] = out.get(cat, 0) + 1
        return out

    def to_block(self, cats: list | None = None) -> str:
        return "\n".join(a.to_block() for a in self.all_attacks())


# `AttackCategory` was always cosmetic — keep as a passthrough for old imports.
class AttackCategory:
    def __init__(self, name: str = "", slug: str = "", attacks: list | None = None) -> None:
        self.name = name
        self.slug = slug
        self.attacks = attacks or []


# Re-export from the richer sub-modules so `from hermes import Persona, ...` works.
try:
    from .persona import PersonaLoader
except ImportError:
    PersonaLoader = None

try:
    from .encoding import Encoder, EncodingScheme
except ImportError:
    Encoder = EncodingScheme = None

try:
    from .provider import ProviderRouter
except ImportError:
    ProviderRouter = None

try:
    from .triad import TriadStack
except ImportError:
    TriadStack = None

try:
    from .compiler import PromptCompiler
except ImportError:
    PromptCompiler = None


__version__ = "1.0.0"
__all__ = [
    "Persona",
    "PersonaLoader",
    "Attack",
    "AttackMatrix",
    "AttackCategory",
    "Triad",
    "TriadStack",
    "Provider",
    "ProviderRouter",
    "PromptCompiler",
    "Encoder",
    "EncodingScheme",
    "BoundaryMethod",
    "main",
    "cli",
    "run_one_attempt",
    "encode_text",
    "is_refusal",
    "iterative_ladder",
    "watch_stream",
]
