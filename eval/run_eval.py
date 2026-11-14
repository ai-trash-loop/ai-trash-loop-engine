"""Evaluation harness. Deterministic detectors only unless --llm is used elsewhere.

Two measurements, kept separate because they answer different questions:

1. SEEDED (precision + recall with known ground truth)
   Copy a clean repo, inject N known defects per type, run the analyzer, and check which seeded
   defects were found. Any finding that is not a seeded defect counts as a false positive, which is
   valid ONLY because the base repo has zero findings. Recall here is recall on *synthetic* defects:
   it measures the detector's mechanics, not how often real-world defects look like these.

2. GOLD (precision on natural findings, human-labeled)
   `export` writes the analyzer's findings on real repos to eval/gold/<repo>.jsonl with label=null.
   A human fills in label: tp | intentional | fp. `score` reports precision per type over labeled rows.
   Unlabeled rows are reported as such; no number is claimed without labels.

Usage:
  python eval/run_eval.py seeded <clean_repo> [--n 10]
  python eval/run_eval.py export <repo> [--out eval/gold/<name>.jsonl]
  python eval/run_eval.py score  eval/gold/<name>.jsonl <repo>
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from trashloop.analyze import analyze


def fkey(f) -> str:
    """Stable identity of a finding: type + sorted evidence locations (not the generated id)."""
    ev = sorted(f"{e.file}:{e.line_start}" for e in f.evidence)
    return f"{f.type.value}|{'|'.join(ev)}"


# ---------- seeded ----------
def seed(root: Path, n: int, rng: random.Random):
    """Inject defects; return {type: [marker, ...]} where marker is a unique string to find in evidence."""
    truth: dict[str, list[str]] = defaultdict(list)
    anchor = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))[0]
    ctx = root / "CLAUDE.md"
    body = ["# Seeded context", ""]
    for i in range(n):
        tag = f"seedbrk{i}"
        body.append(f"See [the {tag} guide](docs/{tag}-missing.md) for details.\n")
        truth["broken_reference"].append(f"{tag}-missing.md")
    for i in range(n):
        tag = f"seedstl{i}"
        body.append(f"The generated output lives in `{anchor}/{tag}/gone/output.py` after each run.\n")
        truth["stale"].append(f"{anchor}/{tag}/gone/output.py")
    texts = []
    for i in range(n):
        t = (f"Always validate input number{i} at the service boundary and reject malformed payloads "
             f"with a descriptive error before touching storage layer{i}.")
        texts.append(t)
        body.append(t + "\n")
        truth["duplicate"].append(f"input number{i} at the service boundary")
    ctx.write_text("\n".join(body))
    # exact copies in a rule file; near copies (a few words appended) in the skill file
    rules = root / ".claude" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / "seed.md").write_text("\n".join(f"- {t}\n" for t in texts[: n // 2]))
    skill = root / ".claude" / "skills" / "seed"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text("\n".join(f"{t} Log the rejection reason too.\n" for t in texts[n // 2 :]))
    return truth


def run_seeded(repo: Path, n: int) -> int:
    base = analyze(repo)
    if base.findings:
        print(f"base repo has {len(base.findings)} findings; seeded precision would be invalid. Use a clean repo.")
        return 2
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "repo"
        shutil.copytree(repo, work, ignore=shutil.ignore_patterns(".git", "node_modules", ".venv"))
        truth = seed(work, n, random.Random(0))
        rep = analyze(work)
    by_type = defaultdict(list)
    for f in rep.findings:
        by_type[f.type.value].append(f)
    print(f"seeded n={n} per type on {repo.name} (base findings: 0)\n")
    print(f"{'type':18} {'seeded':>6} {'found':>6} {'recall':>7} {'reported':>9} {'precision':>10}")
    for typ, markers in truth.items():
        found_markers = {m for m in markers if any(m in " ".join(e.quote + e.file for e in f.evidence) for f in by_type[typ])}
        reported = len(by_type[typ])
        useful = sum(1 for f in by_type[typ] if any(m in " ".join(e.quote for e in f.evidence) for m in markers))
        prec = useful / reported if reported else float("nan")
        print(f"{typ:18} {len(markers):>6} {len(found_markers):>6} {len(found_markers)/len(markers):>7.0%} {reported:>9} {prec:>10.0%}")
        for m in sorted(set(markers) - found_markers):
            print(f"   missed: {m}")
    extra = [t for t in by_type if t not in truth]
    for t in extra:
        print(f"unexpected finding type {t}: {len(by_type[t])}")
    return 0


# ---------- gold ----------
def run_export(repo: Path, out: Path, quotes: bool = False) -> int:
    rep = analyze(repo)
    old = {}
    if out.exists():
        old = {json.loads(l)["key"]: json.loads(l) for l in out.read_text().splitlines() if l.strip()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for f in rep.findings:
            k = fkey(f)
            row = old.get(k) or {"key": k, "type": f.type.value, "label": None, "labeler": None, "note": ""}
            row["summary"] = f.summary
            # Quotes only on request: some fixtures forbid redistribution, so committed gold files carry locations only.
            row["evidence"] = [
                {"file": e.file, "line": e.line_start, **({"quote": e.quote[:160]} if quotes else {})} for e in f.evidence[:3]
            ]
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rep.findings)} rows to {out} (existing labels preserved). Fill `label` with tp|intentional|fp.")
    return 0


def run_score(gold: Path, repo: Path) -> int:
    rows = [json.loads(l) for l in gold.read_text().splitlines() if l.strip()]
    current = {fkey(f) for f in analyze(repo).findings}
    stats = defaultdict(lambda: {"tp": 0, "fp": 0, "unlabeled": 0, "stale_row": 0})
    for r in rows:
        s = stats[r["type"]]
        if r["key"] not in current:
            s["stale_row"] += 1
        elif r["label"] in ("tp", "intentional"):  # an intentional mirror is still a true duplicate
            s["tp"] += 1
        elif r["label"] == "fp":
            s["fp"] += 1
        else:
            s["unlabeled"] += 1
    print(f"{'type':18} {'tp':>4} {'fp':>4} {'precision':>10} {'unlabeled':>10} {'stale rows':>11}")
    for typ, s in sorted(stats.items()):
        lab = s["tp"] + s["fp"]
        p = f"{s['tp']/lab:.0%}" if lab else "n/a"
        print(f"{typ:18} {s['tp']:>4} {s['fp']:>4} {p:>10} {s['unlabeled']:>10} {s['stale_row']:>11}")
    print("\nPrecision is over labeled rows only. Recall on natural findings is not measured (no exhaustive ground truth).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seeded"); s.add_argument("repo", type=Path); s.add_argument("--n", type=int, default=10)
    e = sub.add_parser("export"); e.add_argument("repo", type=Path); e.add_argument("--out", type=Path)
    e.add_argument("--quotes", action="store_true", help="include quoted text (local labeling only; do not commit)")
    c = sub.add_parser("score"); c.add_argument("gold", type=Path); c.add_argument("repo", type=Path)
    a = ap.parse_args()
    if a.cmd == "seeded":
        return run_seeded(a.repo, a.n)
    if a.cmd == "export":
        return run_export(a.repo, a.out or Path(__file__).parent / "gold" / f"{a.repo.resolve().name}.jsonl", a.quotes)
    return run_score(a.gold, a.repo)


if __name__ == "__main__":
    sys.exit(main())
