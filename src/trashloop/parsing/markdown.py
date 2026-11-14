"""Markdown parsing that keeps 1-based line numbers for evidence."""
from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark")
_HTML_ID = re.compile(r"""<a\s[^>]*?(?:id|name)\s*=\s*["']([^"']+)["']""", re.I)


@dataclass(frozen=True)
class Link:
    href: str
    line: int  # 1-based line where the link appears


@dataclass(frozen=True)
class ParsedDoc:
    links: list[Link]
    anchors: set[str]  # GitHub-style heading slugs
    code_spans: list[Link] = ()  # inline `code` spans (href field holds the span text)


def github_slug(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def _inline_text(tok) -> str:
    return "".join(c.content for c in (tok.children or []) if c.type in ("text", "code_inline"))


def parse(text: str) -> ParsedDoc:
    lines = text.splitlines()
    links: list[Link] = []
    spans: list[Link] = []
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    tokens = _md.parse(text)
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            slug = github_slug(_inline_text(tokens[i + 1]))
            n = seen.get(slug, 0)
            seen[slug] = n + 1
            anchors.add(slug if n == 0 else f"{slug}-{n}")
        elif tok.type == "html_block":
            anchors.update(_HTML_ID.findall(tok.content))
        elif tok.type == "inline" and tok.map:
            anchors.update(_HTML_ID.findall(tok.content))
            start, end = tok.map
            for child in tok.children or []:
                if child.type == "code_inline":
                    line = start + 1
                    for ln in range(start, min(end, len(lines))):
                        if child.content in lines[ln]:
                            line = ln + 1
                            break
                    spans.append(Link(href=child.content, line=line))
                if child.type in ("link_open", "image"):
                    href = child.attrGet("href") if child.type == "link_open" else child.attrGet("src")
                    if not href:
                        continue
                    line = start + 1
                    for ln in range(start, min(end, len(lines))):
                        if href in lines[ln]:
                            line = ln + 1
                            break
                    links.append(Link(href=href, line=line))
    return ParsedDoc(links=links, anchors=anchors, code_spans=spans)
