# Provider Rotation

> **ID:** M-05001 | **Category:** Provider | **Tier:** Standard | **Rate:** 70%

Run the same triad against multiple providers in series. First non-refusal
wins. Useful for rate-limited or hard-filtered targets that one provider
will reject but another will accept.

## Form

```python
router = ProviderRouter.from_env(["anthropic", "openai", "deepseek", "xai"])
response, used = router.rotate(messages)
```

## Targets

All chat APIs. Highest pay-off when frontier + open-source providers
disagree on policy.
