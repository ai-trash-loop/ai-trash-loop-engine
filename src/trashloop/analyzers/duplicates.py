"""Deterministic duplicate-instruction detection (ADR 0002: no LLM here).

Exact: identical normalized word sequences. Near: word-3-gram shingle containment
(|A∩B| / min(|A|,|B|)) >= threshold, found via an inverted index so we never compare all pairs.
Related units are clustered (union-find) so one finding describes one redundant idea.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from trashloop.models import ContextFile, Evidence, Finding, FindingType, LoadMode, Method, Severity
from trashloop.parsing.instructions import Unit
from trashloop.scanner.discover import estimate_tokens

NEAR_THRESHOLD = 0.85
MAX_POSTING = 50  # shingles shared by more units than this are boilerplate; skip for candidate generation
MAX_EVIDENCE = 6


def _shingles(words: tuple[str, ...], n: int = 3) -> frozenset[tuple[str, ...]]:
    if len(words) <= n:
        return frozenset([words])
    return frozenset(words[i : i + n] for i in range(len(words) - n + 1))


def _evidence(lines_by_file, u: Unit) -> Evidence:
    q = " ".join(s.strip() for s in lines_by_file[u.file][u.line_start - 1 : u.line_end])[:300]
    return Evidence(file=u.file, line_start=u.line_start, line_end=u.line_end, quote=q)


class _DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        self.p[self.find(a)] = self.find(b)


def find_duplicates(
    units: list[Unit],
    files: dict[str, ContextFile],
    lines_by_file: dict[str, list[str]],
    threshold: float = NEAR_THRESHOLD,
) -> tuple[list[Finding], int]:
    """Return (findings, estimated_tokens_in_redundant_copies)."""
    dsu = _DSU(len(units))
    min_cont: dict[int, float] = {}  # cluster root -> min containment of its edges (1.0 = exact only)

    by_key: dict[str, list[int]] = defaultdict(list)
    for i, u in enumerate(units):
        by_key[u.key].append(i)
    for idxs in by_key.values():
        for j in idxs[1:]:
            dsu.union(idxs[0], j)

    sh = [_shingles(u.words) for u in units]
    postings: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i, s in enumerate(sh):
        for g in s:
            postings[g].append(i)
    shared: Counter[tuple[int, int]] = Counter()
    for idxs in postings.values():
        if 1 < len(idxs) <= MAX_POSTING:
            for a, b in combinations(idxs, 2):
                shared[(a, b)] += 1
    edges: list[tuple[int, int, float]] = []
    for (a, b), cnt in shared.items():
        if units[a].key == units[b].key:
            continue
        c = cnt / min(len(sh[a]), len(sh[b]))
        if c >= threshold:
            edges.append((a, b, c))
            dsu.union(a, b)

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(len(units)):
        clusters[dsu.find(i)].append(i)
    for a, b, c in edges:
        r = dsu.find(a)
        min_cont[r] = min(min_cont.get(r, 1.0), c)

    findings: list[Finding] = []
    est_tokens = 0
    n = 0
    for root, idxs in sorted(clusters.items(), key=lambda kv: min(kv[1])):
        if len(idxs) < 2:
            continue
        # a cluster of identical text in one place isn't a duplicate across locations
        us = sorted((units[i] for i in idxs), key=lambda u: (u.file, u.line_start))
        keep = max(us, key=lambda u: len(u.words))  # canonical copy = the fullest one
        est_tokens += sum(estimate_tokens(u.key) for u in us if u is not keep)
        exact = root not in min_cont
        sev = Severity.MEDIUM if all(files[u.file].load_mode == LoadMode.ALWAYS for u in us) else Severity.LOW
        n += 1
        shown = us[:MAX_EVIDENCE]
        more = f" (+{len(us) - MAX_EVIDENCE} more)" if len(us) > MAX_EVIDENCE else ""
        findings.append(Finding(
            id=f"dup-{n:04d}", type=FindingType.DUPLICATE, severity=sev,
            confidence=1.0 if exact else round(min(0.9, min_cont[root] * 0.9), 2), method=Method.DETERMINISTIC,
            summary=(f"Same instruction appears {len(us)} times (identical after normalization)" if exact
                     else f"{len(us)} near-duplicate instructions (>= {min_cont[root]:.0%} of the shorter text shared){more}"),
            evidence=[_evidence(lines_by_file, u) for u in shown],
            recommendation="Keep one canonical copy and link to it. If the copies are an intentional mirror, document that.",
        ))
    return findings, est_tokens
