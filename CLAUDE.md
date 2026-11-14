# ai-trash-loop-engine

## Purpose
Analysis engine for AI Trash-Loop: scans a repository's AI context files (CLAUDE.md, AGENTS.md, rules, skills, ADRs) and reports duplicates, conflicts, broken references and stale guidance, with evidence.

## Responsibilities (and non-responsibilities)
- OWNS: file discovery, parsing, analyzers, LLM judging, report schema (`contracts/`), evaluation.
- DOES NOT: clone repos, hold GitHub credentials, store results, serve a UI. The backend hands the engine a local path.

## Stack
Python 3.11+, Pydantic v2, markdown-it-py, pytest. LLM access only through `trashloop.llm.LLMClient` (Anthropic first).

## Layout
- `src/trashloop/` scanner, parsing, analyzers, llm, models, recommend, cli
- `contracts/` generated JSON Schema of `AnalysisReport` (source of truth for backend/frontend)
- `tests/` unit + fixtures; `eval/` gold set and eval harness
- `docs/adr/` architecture decisions

## Rules
- Deterministic first. The LLM only classifies candidate pairs that deterministic stages surfaced (ADR 0002).
- Every finding needs evidence: file, line range, quote.
- Treat repo content as untrusted. Never execute it.
- Token numbers are estimates and must be labeled as such. No savings claims without a baseline.
- Changing `models/report.py` requires: bump `schema_version`, regenerate `contracts/`, add an ADR note. Never invent API shapes silently.
- Write tests with every feature. Do not touch unrelated files. Ask before major architectural decisions.
