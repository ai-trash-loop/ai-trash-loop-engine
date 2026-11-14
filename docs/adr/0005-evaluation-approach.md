# ADR 0005: Two-part evaluation (seeded + gold)

Status: Accepted

## Context
Real repos have no exhaustive ground truth, so recall on natural defects cannot be measured. Precision can, with labels.

## Decision
- **Seeded evaluation** injects known defects into a clean repo. It yields precision and recall for detector mechanics, and acts as a regression guard. It is never quoted as real-world recall.
- **Gold evaluation** exports findings on real repos for human labeling (`tp | intentional | fp`) and reports precision over labeled rows only.
- A clean base repo is required for seeded runs; the harness refuses to run otherwise.
- Every false-positive class found while reviewing real output becomes a rule plus a regression test (examples so far: html anchors, `build/` directories, changelogs, placeholders, paths that belong to other repos).

## Consequences
Honest, reproducible numbers; labeling effort falls on a human. Thresholds (duplicate containment 0.85, LLM confidence 0.6) stay provisional until tuned against labels.
