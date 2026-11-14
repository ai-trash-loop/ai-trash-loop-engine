"""Semantic duplicate and conflict detection (ADR 0002).

Deterministic candidate generation (scope overlap + content-word overlap, ranked, capped),
then an LLM judge classifies each candidate. The LLM never discovers pairs on its own.
"""
from __future__ import annotations

import re

from trashloop.analyzers.scope import overlaps
from trashloop.llm.client import LLMClient
from trashloop.models import ContextFile, Evidence, Finding, FindingType, Method, Severity
from trashloop.parsing.instructions import Unit

STOP = frozenset("""a an the and or but if then else of to in on for with by at from as is are was were be been being it its this that
these those you your we our they their not no do does did done can could should would may might must will shall have has had
use used using when whenever before after into out up so than too very also any all each every only just more most such""".split())

MIN_JACCARD = 0.25
MIN_CONFIDENCE = 0.6


def _content(u: Unit) -> frozenset[str]:
    return frozenset(w for w in u.words if w not in STOP and len(w) > 2 and not w.isdigit())


def candidate_pairs(
    units: list[Unit], scopes: dict[str, frozenset[str]], skip: set[frozenset[tuple[str, int]]], limit: int
) -> list[tuple[float, Unit, Unit]]:
    cw = [_content(u) for u in units]
    out: list[tuple[float, Unit, Unit]] = []
    for i in range(len(units)):
        if len(cw[i]) < 3:
            continue
        for j in range(i + 1, len(units)):
            a, b = units[i], units[j]
            if len(cw[j]) < 3 or (a.file == b.file and a.line_start == b.line_start):
                continue
            if frozenset([(a.file, a.line_start), (b.file, b.line_start)]) in skip:
                continue
            inter = len(cw[i] & cw[j])
            if inter < 3:
                continue
            jac = inter / len(cw[i] | cw[j])
            if jac >= MIN_JACCARD and overlaps(scopes[a.file], scopes[b.file]):
                out.append((jac, a, b))
    out.sort(key=lambda t: -t[0])
    return out[:limit]


def _text(lines_by_file, u: Unit) -> str:
    return " ".join(s.strip() for s in lines_by_file[u.file][u.line_start - 1 : u.line_end])[:600]


def find_semantic(
    units: list[Unit],
    files: dict[str, ContextFile],
    lines_by_file: dict[str, list[str]],
    scopes: dict[str, frozenset[str]],
    judge: LLMClient,
    skip: set[frozenset[tuple[str, int]]],
    max_pairs: int = 50,
) -> tuple[list[Finding], int, int, int]:
    """Return (findings, llm_input_tokens, llm_output_tokens, pairs_judged)."""
    findings: list[Finding] = []
    tin = tout = judged = 0
    n = 0
    for _, a, b in candidate_pairs(units, scopes, skip, max_pairs):
        ta, tb = _text(lines_by_file, a), _text(lines_by_file, b)
        note = f"a applies to {sorted(scopes[a.file])}; b applies to {sorted(scopes[b.file])}"
        verdict, usage = judge.judge_pair(ta, tb, note)
        tin += usage.input_tokens
        tout += usage.output_tokens
        judged += 1
        if verdict is None or verdict.confidence < MIN_CONFIDENCE or verdict.relation not in ("duplicate", "conflict"):
            continue
        n += 1
        ev = [
            Evidence(file=u.file, line_start=u.line_start, line_end=u.line_end, quote=t[:300])
            for u, t in ((a, ta), (b, tb))
        ]
        is_conflict = verdict.relation == "conflict"
        findings.append(Finding(
            id=f"sem-{n:04d}", type=FindingType.CONFLICT if is_conflict else FindingType.DUPLICATE,
            severity=Severity.HIGH if is_conflict else Severity.LOW, confidence=verdict.confidence,
            method=Method.LLM, summary=f"[{judge.model}] {verdict.relation}: {verdict.rationale}", evidence=ev,
            recommendation=("Decide which instruction wins and remove or scope the other so agents don't oscillate."
                            if is_conflict else "These express the same requirement; keep one and reference it."),
        ))
    return findings, tin, tout, judged
