# Early-Stop Stream Watch

> **ID:** M-07001 | **Category:** Stream | **Tier:** Advanced | **Rate:** 70%

Abort streaming completions that begin with a refusal pattern within the
first ~50 tokens. Refusal is high-entropy in the prefix; a non-refusal
sigil can be detected cheaply. Retry with the next triad plan on abort.

## Form

```python
from hermes.stream import watch, StreamPredicate
result = watch(provider.stream(messages))
if result.aborted:
    apply_iterative(messages)
```

## Targets

All streaming-capable chat APIs. OpenAI, Anthropic, OpenRouter, and any
self-hosted Hermes-shaped server.
