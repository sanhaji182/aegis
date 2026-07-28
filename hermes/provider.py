"""Multi-provider router — INCES M-015 / 05-multi-provider.

Targets 55+ model providers via unified API. Each provider exposes:
- `name`           stable slug
- `id_kind`        "openai-anthropic"/"openai"/"anthropic"/"custom"
- `chat(messages)` → text response
- `stream(messages)` → iterator of tokens

Built-in providers handle the well-known corporate endpoints plus a generic
`custom:URL` pattern for self-hosted Hermes-shaped servers.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import httpx


@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    api_key: str | None = None
    id_kind: str = "openai"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 120.0
    max_tokens: int = 4096

    def chat(self, messages: list[dict[str, Any]], **kwargs) -> str:
        """Single-shot chat completion."""
        return self._chat(messages, stream=False, **kwargs)

    def stream(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> Iterable[str]:
        """Token-by-token streaming."""
        return self._chat(messages, stream=True, **kwargs)

    def _chat(
        self,
        messages: list[dict[str, Any]],
        stream: bool,
        **kwargs,
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 1.0),
        }
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if not stream:
            r = httpx.post(
                url, headers=headers, json=payload, timeout=self.timeout
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

        def _iter() -> Iterable[str]:
            with httpx.stream(
                "POST", url, headers=headers, json=payload, timeout=self.timeout
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    if line.strip() == "data: [DONE]":
                        break
                    try:
                        payload = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    for choice in payload.get("choices", []):
                        delta = choice.get("delta", {}).get("content")
                        if delta:
                            yield delta

        return _iter()


# ── provider registry ─────────────────────────────────────────────────


PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model_default": "gpt-4o",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model_default": "claude-sonnet-4-5",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model_default": "anthropic/claude-sonnet-4-5",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model_default": "llama-3.3-70b-versatile",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model_default": "deepseek-chat",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "model_default": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "model_default": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "model_default": "grok-2",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model_default": "mistral-large-latest",
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/v1",
        "model_default": "command-r-plus",
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "model_default": "llama-3.1-sonar-large-128k-online",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model_default": "gemini-2.5-pro",
    },
}


class ProviderRouter:
    """Multi-provider dispatch + parallel ensemble.

    Patterns (M-015):
    - rotation   : try each provider in turn until one returns content
    - parallel   : broadcast same prompt, collect responses
    - ensemble   : run N and pick best by simple length/sentiment heuristic

    Configurable per-run via `route.run(...)`.
    """

    def __init__(self, providers: list[Provider]):
        if not providers:
            raise ValueError("ProviderRouter needs at least one Provider.")
        self.providers = providers

    @classmethod
    def from_env(
        cls, keys: list[str] | None = None, custom_urls: dict[str, str] | None = None
    ) -> "ProviderRouter":
        """Build a router from env vars.

        For each preset name in `keys`, read `HERMES_API_KEY_<NAME>` and
        `HERMES_MODEL_<NAME>` (optional override).
        """
        keys = keys or ["anthropic", "openai", "deepseek"]
        urls = custom_urls or {}
        out: list[Provider] = []
        for name in keys:
            preset = PRESETS.get(name)
            if not preset:
                continue
            api_key = os.environ.get(f"HERMES_API_KEY_{name.upper()}")
            model = os.environ.get(f"HERMES_MODEL_{name.upper()}", preset["model_default"])
            base_url = urls.get(name, preset["base_url"])
            out.append(
                Provider(name=name, base_url=base_url, model=model, api_key=api_key)
            )
        if not out:
            raise ValueError(
                "No providers could be loaded from env. Set HERMES_API_KEY_<NAME> "
                "or pass explicit Provider objects."
            )
        return cls(out)

    # ── dispatch ────────────────────────────────────────────────

    def rotate(self, messages: list[dict[str, Any]]) -> tuple[str, str]:
        """Try each provider in order; first non-empty wins."""
        for p in self.providers:
            try:
                out = p.chat(messages).strip()
                if out:
                    return out, p.name
            except Exception:
                continue
        raise RuntimeError("All providers refused or returned empty.")

    def parallel(self, messages: list[dict[str, Any]]) -> dict[str, str]:
        """Broadcast; collect every provider's response."""
        out: dict[str, str] = {}
        for p in self.providers:
            try:
                out[p.name] = p.chat(messages)
            except Exception as e:
                out[p.name] = f"[error: {e}]"
        return out

    def best_of(
        self, messages: list[dict[str, Any]], k: int = 3
    ) -> tuple[str, str]:
        """Pick the longest valid response; ties broken by provider order."""
        responses = self.parallel(messages)
        ranked = sorted(
            ((name, len(text), text) for name, text in responses.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        for _, length, text in ranked[:k]:
            if length > 0 and not text.startswith("[error"):
                return text, ranked[0][0]
        raise RuntimeError("No usable responses from any provider.")
