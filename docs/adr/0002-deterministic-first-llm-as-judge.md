# ADR 0002: Deterministic first, LLM as judge only

Status: Accepted

## Context
LLM calls cost money, add latency and can hallucinate. Many findings (broken links, exact duplicates, stale paths) need no semantics.

## Decision
- Deterministic stages find candidates: reference validation, hashing/MinHash duplicates, scope resolution.
- The LLM only classifies candidate pairs (duplicate / conflict / compatible / unrelated) and phrases recommendations. It never discovers findings on its own.
- LLM output is structured, schema-validated, cached on disk by (model, prompt version, input hash), and retried with backoff.
- Each finding records `method: deterministic | llm`.

## Consequences
Lower cost, reproducible CI via cached responses, and evaluable detectors. Recall of semantic findings is bounded by candidate generation, so candidate recall is measured separately in eval.
