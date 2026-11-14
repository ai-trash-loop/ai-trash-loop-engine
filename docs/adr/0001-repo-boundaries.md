# ADR 0001: Three repositories with strict boundaries

Status: Accepted

## Context
The product has an analysis engine, an orchestration backend and a UI. We want independent testability and clear ownership.

## Decision
- **engine**: analysis, LLM use, evaluation, report schema. Pure library plus CLI; optional thin HTTP wrapper.
- **backend**: GitHub access and cloning, job management, persistence, API for the UI. Calls the engine with a local path and receives an `AnalysisReport`.
- **frontend**: visualization only; talks to the backend via its documented API.

The engine never touches GitHub credentials. The backend never contains analysis logic.

## Consequences
Contract changes touch up to three repos, so the contract lives in one place (ADR 0003).
