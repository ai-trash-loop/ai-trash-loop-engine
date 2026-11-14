from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from trashloop import __version__
from trashloop.analyzers.duplicates import find_duplicates
from trashloop.analyzers.references import check_references
from trashloop.analyzers.scope import scope_of
from trashloop.analyzers.semantic import find_semantic
from trashloop.analyzers.stale import check_stale
from trashloop.llm.client import LLMClient
from trashloop.models import AnalysisReport, FileKind, LoadMode, Metrics, RepoInfo
from trashloop.parsing.instructions import extract_units
from trashloop.parsing.markdown import parse
from trashloop.scanner.discover import discover

# Duplicates/conflicts are only meaningful across agent-instruction files, not ADRs/docs (ADR 0002 scoping).
DUP_KINDS = {FileKind.CLAUDE_MD, FileKind.AGENTS_MD, FileKind.RULE, FileKind.SKILL}

# Only skip dirs that are never part of a link target; build/, bin/ etc. can hold real tracked files.
_EXISTENCE_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def _all_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part in _EXISTENCE_SKIP for part in rel.parts) or p.is_symlink():
            continue
        paths.add(rel.as_posix())
    return paths


def analyze(root: Path, judge: LLMClient | None = None, max_llm_pairs: int = 50) -> AnalysisReport:
    """Analyze a local checkout. Deterministic unless `judge` is given (then candidate pairs are LLM-judged)."""
    t0 = time.perf_counter()
    root = root.resolve()
    found = discover(root)
    docs = {cf.path: (parse(text), text.splitlines()) for cf, text in found}
    paths = _all_paths(root)
    findings = check_references(docs, paths) + check_stale(docs, paths)
    files = [cf for cf, _ in found]
    by_path = {cf.path: cf for cf in files}

    scoped = [(cf, t) for cf, t in found if cf.kind in DUP_KINDS]
    lines_by_file = {cf.path: t.splitlines() for cf, t in scoped}
    units = [u for cf, t in scoped for u in extract_units(cf.path, t)]
    dup_findings, dup_tokens = find_duplicates(units, by_path, lines_by_file)
    findings += dup_findings

    tin = tout = 0
    if judge is not None:
        scopes = {cf.path: scope_of(cf.path, t, cf.load_mode == LoadMode.ALWAYS) for cf, t in scoped}
        already = {  # unit pairs the deterministic stage already reported
            frozenset([(a.file, a.line_start), (b.file, b.line_start)])
            for f in dup_findings
            for a in [f.evidence[0]]
            for b in f.evidence[1:]
        }
        sem, tin, tout, _ = find_semantic(units, by_path, lines_by_file, scopes, judge, already, max_llm_pairs)
        findings += sem

    return AnalysisReport(
        engine_version=__version__,
        repo=RepoInfo(name=root.name),
        analyzed_at=datetime.now(timezone.utc),
        context_files=files,
        findings=findings,
        metrics=Metrics(
            files_scanned=len(files),
            est_tokens_total=sum(f.token_estimate for f in files),
            est_tokens_duplicated=dup_tokens,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            llm_input_tokens=tin,
            llm_output_tokens=tout,
        ),
    )
