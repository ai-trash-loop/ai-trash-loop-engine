# ai-trash-loop-engine

Analyzes a repository's AI context files (CLAUDE.md, AGENTS.md, rules, skills, ADRs) and reports
broken references, stale paths, duplicate instructions and (with an LLM judge) semantic duplicates and conflicts.
Every finding carries evidence: file, line range, quote.

## Quick start
```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev,llm]'
.venv/bin/pytest
.venv/bin/trashloop analyze /path/to/repo --out report.json          # deterministic, free
.venv/bin/trashloop analyze /path/to/repo --llm --max-llm-pairs 30   # + LLM judge (needs ANTHROPIC_API_KEY, costs money)
```
The report schema is `contracts/analysis_report.schema.json` (generated from `src/trashloop/models/report.py`).

## Design
Deterministic stages find candidates; the LLM only classifies candidate pairs (ADR 0002). LLM calls are cached
on disk by (model, prompt version, inputs), capped by `--max-llm-pairs`, and repo text is passed as untrusted data.

| Stage | Module | Uses LLM |
|---|---|---|
| discovery, parsing | `scanner/`, `parsing/` | no |
| broken links/anchors | `analyzers/references.py` | no |
| stale paths | `analyzers/stale.py` | no |
| exact/near duplicates | `analyzers/duplicates.py` | no |
| semantic duplicates, conflicts | `analyzers/semantic.py`, `analyzers/scope.py`, `llm/` | candidate pairs only |

## Evaluation
Fixtures are fetched from upstream at pinned commits (`eval/fetch_fixtures.sh`; see [eval/FIXTURES.md](eval/FIXTURES.md) for licenses).
```bash
eval/fetch_fixtures.sh fixtures
.venv/bin/python eval/run_eval.py seeded fixtures/agents-adrs     # synthetic ground truth
.venv/bin/python eval/run_eval.py export fixtures/just-dummies    # write findings for hand labeling
.venv/bin/python eval/run_eval.py score eval/gold/just-dummies.jsonl fixtures/just-dummies
```
Metric definitions and caveats: [docs/metrics.md](docs/metrics.md). Decisions: [docs/adr/](docs/adr/).

## Known limitations
- Markdown only; no code analysis. Instruction extraction = paragraphs and list items of at least 8 words.
- Scope modeling is an approximation (frontmatter globs or directory); see `analyzers/scope.py`.
- LLM detectors are implemented and unit-tested with a fake judge, but not yet evaluated against labeled pairs.
- Duplicate threshold is provisional until tuned on labels.

## License
MIT. See [LICENSE](LICENSE). Third-party fixtures keep their own licenses (see eval/FIXTURES.md).
