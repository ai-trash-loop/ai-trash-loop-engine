# ADR 0004: Thin LLM client, Anthropic first

Status: Accepted

## Decision
All LLM calls go through one `LLMClient` interface (`judge_pair`, `phrase_recommendation`). The first implementation uses the Anthropic SDK; default judge model is Haiku-class, compared against Sonnet-class in eval. A second provider (free-tier or local) may be added later for comparison. No other module imports a provider SDK.

Usage (input/output tokens, cache hits) is recorded per call and surfaced in report `metrics`.

## Consequences
Models can be swapped and compared in eval without touching analyzers; tests use recorded responses.
