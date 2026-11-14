"""Deterministic broken-reference detection for markdown links."""
from __future__ import annotations

import posixpath
import unicodedata
from urllib.parse import unquote

from trashloop.models import Evidence, Finding, FindingType, Method, Severity
from trashloop.parsing.markdown import ParsedDoc

_SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "ftp://")
_TEMPLATE_CHARS = set("{}<>$*")


def _norm_anchor(a: str) -> str:
    """Renderers disagree on diacritics and trailing hyphens ("vous-même" vs "vous-meme", "dummy ?" -> "dummy-").
    We compare leniently so renderer-dependent links are not reported as broken."""
    d = unicodedata.normalize("NFKD", a.lower())
    return "".join(c for c in d if not unicodedata.combining(c)).strip("-")


def check_references(docs: dict[str, tuple[ParsedDoc, list[str]]], all_paths: set[str]) -> list[Finding]:
    """docs: rel_path -> (parsed, source lines). all_paths: every file/dir path in repo (posix, relative)."""
    findings: list[Finding] = []
    n = 0
    for rel, (doc, lines) in docs.items():
        base = posixpath.dirname(rel)
        for link in doc.links:
            href = unquote(link.href.strip())  # markdown-it percent-encodes e.g. { }
            if not href or href.startswith(_SKIP_PREFIXES) or _TEMPLATE_CHARS & set(href):
                continue
            target, _, frag = href.partition("#")
            target = unquote(target).split("?")[0]
            if not target:  # same-file anchor
                dest, ok = rel, True
            else:
                dest = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join(base, target))
                ok = dest in all_paths
            reason = None
            if not ok:
                reason = f"link target '{target}' does not exist"
            elif frag and dest in docs:
                if _norm_anchor(unquote(frag)) not in {_norm_anchor(x) for x in docs[dest][0].anchors}:
                    reason = f"anchor '#{frag}' not found in {dest}"
            if reason:
                n += 1
                quote = lines[link.line - 1].strip() if link.line - 1 < len(lines) else href
                findings.append(Finding(
                    id=f"ref-{n:04d}", type=FindingType.BROKEN_REFERENCE, severity=Severity.MEDIUM,
                    confidence=0.95, method=Method.DETERMINISTIC, summary=f"{rel}: {reason}",
                    evidence=[Evidence(file=rel, line_start=link.line, line_end=link.line, quote=quote[:300])],
                    recommendation="Fix the path or remove the reference so agents don't follow a dead link.",
                ))
    return findings
