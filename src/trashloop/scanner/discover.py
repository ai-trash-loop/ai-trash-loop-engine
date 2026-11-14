"""Context file discovery. Reads files only; never executes anything from the repo."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from trashloop.models import ContextFile, FileKind, LoadMode

SKIP_DIRS = {".git", "node_modules", "target", "bin", "obj", ".venv", "venv", "dist", "build", "__pycache__"}
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 5000


def classify(rel: str) -> tuple[FileKind, LoadMode]:
    p = PurePosixPath(rel)
    name = p.name.lower()
    parts = [x.lower() for x in p.parts]
    if name == "claude.md":
        return FileKind.CLAUDE_MD, LoadMode.ALWAYS
    if name == "agents.md":
        return FileKind.AGENTS_MD, LoadMode.ALWAYS
    if ".claude" in parts and "rules" in parts:
        return FileKind.RULE, LoadMode.UNKNOWN  # rules may be path-scoped; resolved later
    if name == "skill.md" or "skills" in parts and ".claude" in parts:
        return FileKind.SKILL, LoadMode.ON_DEMAND
    if "adr" in parts or "adrs" in parts or "decisions" in parts:
        return FileKind.ADR, LoadMode.ON_DEMAND
    if name.startswith("readme"):
        return FileKind.README, LoadMode.ON_DEMAND
    return FileKind.DOC, LoadMode.ON_DEMAND


def estimate_tokens(text: str) -> int:
    """Rough ESTIMATE (~4 chars/token). Not an exact tokenizer count."""
    return (len(text) + 3) // 4


def discover(root: Path) -> list[tuple[ContextFile, str]]:
    """Return (ContextFile, text) for every markdown file under root."""
    root = root.resolve()
    out: list[tuple[ContextFile, str]] = []
    stack = [root]
    while stack and len(out) < MAX_FILES:
        d = stack.pop()
        for entry in sorted(d.iterdir()):
            if entry.is_symlink():
                continue  # never follow symlinks out of the repo
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
            elif entry.suffix.lower() == ".md" and entry.stat().st_size <= MAX_FILE_BYTES:
                text = entry.read_text(encoding="utf-8", errors="replace")
                rel = entry.relative_to(root).as_posix()
                kind, mode = classify(rel)
                out.append((ContextFile(path=rel, kind=kind, token_estimate=estimate_tokens(text), load_mode=mode), text))
    out.sort(key=lambda t: t[0].path)
    return out
