"""Extract instruction units (paragraphs and list items) with line spans."""
from __future__ import annotations

import re
from dataclasses import dataclass

from trashloop.parsing.markdown import _md

_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class Unit:
    file: str
    line_start: int  # 1-based, inclusive
    line_end: int
    words: tuple[str, ...]  # normalized, lowercase

    @property
    def key(self) -> str:
        return " ".join(self.words)


def _inline_words(tok) -> tuple[str, ...]:
    parts: list[str] = []
    for c in tok.children or []:
        if c.type in ("text", "code_inline"):
            parts.append(c.content)
        elif c.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return tuple(w.lower() for w in _WORD.findall(" ".join(parts)))


def extract_units(file: str, text: str, min_words: int = 8) -> list[Unit]:
    tokens = _md.parse(text)
    units: list[Unit] = []
    for i, tok in enumerate(tokens):
        if tok.type == "inline" and i > 0 and tokens[i - 1].type == "paragraph_open" and tok.map:
            words = _inline_words(tok)
            if len(words) >= min_words:
                units.append(Unit(file, tok.map[0] + 1, tok.map[1], words))
    return units
