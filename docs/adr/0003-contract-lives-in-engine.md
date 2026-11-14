# ADR 0003: Report contract lives in the engine repo

Status: Accepted

## Decision
`AnalysisReport` is defined as Pydantic models in `src/trashloop/models/`. A JSON Schema is generated into `contracts/analysis_report.schema.json` and committed. Backend (Pydantic) and frontend (TypeScript) types are generated from that file. The report carries `schema_version` (semver); breaking changes bump the major version.

## Consequences
One source of truth, no hand-copied types. CI in each repo should verify its generated types match the schema version it targets.
