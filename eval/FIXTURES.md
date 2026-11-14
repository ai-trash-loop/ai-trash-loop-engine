# Evaluation fixtures

Third-party repositories used as analysis targets. They are **not** vendored here; fetch them with
`eval/fetch_fixtures.sh`, which clones each at the pinned commit.

| Fixture | Upstream | Pinned commit | License | Role |
|---|---|---|---|---|
| agents-adrs | github.com/gmoigneu/agents-adrs | `a36a1063` | CC BY 4.0 (content), MIT (code) | Clean base for seeded evaluation (0 findings) |
| just-dummies | github.com/Reefact/just-dummies | `522a73de` | PolyForm Internal Use 1.0.0 | Real-world stress test; gold labels in `gold/just-dummies.jsonl` |
| spring-petclinic-modulith | github.com/spring-petclinic/spring-petclinic-modulith | `58c3310e` | Apache 2.0 | Negative control (no agent context) |

## Licensing notes
- **just-dummies must not be redistributed** (PolyForm Internal Use forbids distribution). That is why it is fetched
  from upstream and why `gold/just-dummies.jsonl` stores only file paths, line numbers, finding types and labels,
  not quoted text. `export` omits quotes unless you pass `--quotes` (for local labeling only; do not commit that output).
- A mirror of the two permissively licensed fixtures, with attribution, is at github.com/ai-trash-loop/ai-trash-loop-fixtures.
- Gold labels apply to the pinned commit. Findings and line numbers can change at other commits.
- Gold labels are `claude-provisional` until a human reviews them. See `docs/metrics.md`.
