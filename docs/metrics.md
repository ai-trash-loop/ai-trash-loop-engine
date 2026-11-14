# Metrics: definitions and how each is measured

Nothing here is a savings claim. Figures marked *estimate* are approximations by construction.

| Metric | Definition | Method | Caveat |
|---|---|---|---|
| `est_tokens_total` | Estimated tokens in all discovered markdown files | characters / 4, rounded up | Estimate, not a tokenizer count. Includes on-demand docs, so it is NOT context loaded per session. |
| `est_tokens_duplicated` | Estimated tokens in redundant copies inside agent-instruction files | per duplicate cluster, sum of all copies except the fullest one | Estimate. Says how much text is repeated, not how many tokens an agent actually loads or could save. |
| Seeded recall | Seeded defects detected / defects seeded | `eval/run_eval.py seeded` on a clean repo | Synthetic defects: tests detector mechanics, not real-world recall. |
| Seeded precision | Findings matching a seeded defect / findings reported | same, valid only because the base repo has 0 findings | Same caveat. |
| Gold precision | (tp + intentional) / labeled findings, per type | human labels in `eval/gold/*.jsonl`, `run_eval.py score` | Only over labeled rows. Intentional mirrors count as true duplicates. |
| Natural recall | Not measured | no exhaustive ground truth exists for real repos | Do not quote a recall figure for real repos. |
| `llm_input_tokens` / `llm_output_tokens` | Tokens the judge consumed in this run | summed from API `usage`; 0 on cache hits | Real API usage, not an estimate. |
| `duration_ms` | Wall time of `analyze()` | `perf_counter` | Includes LLM latency when a judge is used. |

## Per-detector status

| Detector | Method | Evaluated how |
|---|---|---|
| broken_reference | deterministic | seeded + gold |
| stale | deterministic (anchored paths only, see module docstring) | seeded + gold |
| duplicate (exact / near) | deterministic, threshold 0.85 containment | seeded + gold; threshold not yet tuned on labels |
| duplicate (semantic) / conflict | LLM judge on deterministic candidate pairs | **not yet evaluated** (needs labeled pairs and an API key) |

## Current gold results (just-dummies, labeler: claude-provisional)

| Type | tp (incl. intentional) | fp | Precision |
|---|---|---|---|
| broken_reference | 16 | 0 | 100% |
| duplicate | 33 | 0 | 100% |
| stale | 2 | 5 | 29% |

Read these with care:
- Labels were assigned by Claude, not a human, and are marked `claude-provisional`. They need human spot-checks.
- Detector rules (diacritic-tolerant anchors, history/migration skipping, French cues) were tuned on this same data, so these numbers are optimistic. A held-out repo is needed for an honest figure.
- 29 of the 33 duplicate rows are the documented AGENTS.md mirror (label `intentional`): correct detections that a maintainer may deliberately keep.
- One duplicate (adr-check skill "four outcomes" vs AGENTS.md "three outcomes") looks like real drift between copies.
- Stale precision is low; its remaining false positives are paths inside generated trial projects.
