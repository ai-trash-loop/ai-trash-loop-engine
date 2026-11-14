"""Deterministic stale-reference detection: `code spans` that look like repo paths but don't exist.

Precision rules (learned from agents-adrs, where the first version was 0/8 correct; that repo
documents OTHER repos' files):
- only slash paths are considered; bare filenames ("CLAUDE.md", "setup.py") are too ambiguous;
- the path must be ANCHORED here: its first segment exists in this repo (top level, or next to the file);
  so `src/gone/old.py` is flagged when `src/` exists, but `America/New_York` and `.claude/...` are not
  when no such directory exists;
- changelogs/release notes/migration docs are skipped (they describe history, so removed paths are expected);
- placeholder tokens (xxx, NN, ...) are skipped;
- lines that say a path is gone ("not ported", "renamed", "upstream", "formerly"...) are skipped;
- paths containing an ellipsis are skipped;
- lines that introduce examples ("e.g.", "for example", "such as") are skipped.
Limitation: a reference whose whole top-level directory was deleted is not detected.
"""
from __future__ import annotations

import posixpath
import re

from trashloop.models import Evidence, Finding, FindingType, Method, Severity
from trashloop.parsing.markdown import ParsedDoc

_PATH = re.compile(r"^\.{0,2}/?[\w.\-]+(?:/[\w.\-]+)+/?$")
_EXAMPLE = re.compile(r"\b(e\.g\.|for example|for instance|such as|i\.e\.)", re.I)
_HISTORICAL = re.compile(r"\b(not ported|was not|were not|no longer|renamed|removed|formerly|previously|upstream|legacy|deprecated|used to|replaced by|moved to|amont|pas été porté|porté|renomm\w+|supprimé\w*|ancien\w*)\b", re.I)
_BAD = set("*<>{}$|\\ ~")
_HISTORY = re.compile(r"(?:^|/)(?:changelog|release[_-]?notes|history|news|migration)[^/]*(?:/|$)", re.I)
_PLACEHOLDER = re.compile(r"(?:x{2,}|\bNN\b|\d[nN]{2}|\{|\bXX)", re.I)
_URLISH = re.compile(r"^(?:https?:|www\.|@|\w+://)")


def check_stale(docs: dict[str, tuple[ParsedDoc, list[str]]], all_paths: set[str]) -> list[Finding]:
    top = {p.split("/")[0] for p in all_paths}
    out: list[Finding] = []
    n = 0
    for rel, (doc, lines) in docs.items():
        if _HISTORY.search(rel):
            continue
        base = posixpath.dirname(rel)
        for span in doc.code_spans:
            t = span.href.strip()
            if not t or _BAD & set(t) or _URLISH.match(t):
                continue
            if not _PATH.match(t) or _PLACEHOLDER.search(t) or "..." in t:
                continue
            norm = posixpath.normpath(t.lstrip("/")) if t.startswith("/") else posixpath.normpath(t)
            first = norm.split("/")[0]
            anchored = first in top or posixpath.join(base, first) in all_paths
            if not anchored:
                continue
            cands = {norm, posixpath.normpath(posixpath.join(base, t))}
            if any(c in all_paths for c in cands):
                continue
            line_text = lines[span.line - 1] if span.line - 1 < len(lines) else ""
            if _EXAMPLE.search(line_text) or _HISTORICAL.search(line_text):
                continue
            n += 1
            quote = lines[span.line - 1].strip() if span.line - 1 < len(lines) else t
            out.append(Finding(
                id=f"stale-{n:04d}", type=FindingType.STALE, severity=Severity.LOW, confidence=0.6,
                method=Method.DETERMINISTIC,
                summary=f"{rel}: referenced path `{t}` not found in the repository",
                evidence=[Evidence(file=rel, line_start=span.line, line_end=span.line, quote=quote[:300])],
                recommendation="Update or remove the path. If it is a generated or external artifact, say so in the text.",
            ))
    return out
