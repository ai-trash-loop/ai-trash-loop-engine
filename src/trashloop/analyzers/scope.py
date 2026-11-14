"""Approximate instruction scope. A conflict only matters if both instructions can apply together.

Approximation (documented, deliberately simple): a file's scope is
- the `paths:`/`globs:` list in its YAML frontmatter, if present (Claude Code rules), else
- the directory it lives in for nested CLAUDE.md/AGENTS.md, else global ("").
Two scopes overlap if either is global, or any two globs share a literal prefix.
"""
from __future__ import annotations

import posixpath
import re

_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def scope_of(path: str, text: str, always_global: bool) -> frozenset[str]:
    m = _FM.match(text)
    if m:
        block = m.group(1)
        globs = re.findall(r"^\s*-\s*[\"']?([^\"'\n]+?)[\"']?\s*$", block, re.M)
        inline = re.search(r"^(?:paths|globs):\s*\[(.*?)\]", block, re.M)
        if inline:
            globs += [g.strip(" \"'") for g in inline.group(1).split(",") if g.strip()]
        if globs:
            return frozenset(globs)
    d = posixpath.dirname(path)
    if always_global and d and not d.startswith(".claude"):
        return frozenset([d + "/"])
    return frozenset([""])


def _prefix(g: str) -> str:
    return re.split(r"[*?\[{]", g, maxsplit=1)[0]


def overlaps(a: frozenset[str], b: frozenset[str]) -> bool:
    if "" in a or "" in b:
        return True
    for x in a:
        for y in b:
            px, py = _prefix(x), _prefix(y)
            if px.startswith(py) or py.startswith(px):
                return True
    return False
