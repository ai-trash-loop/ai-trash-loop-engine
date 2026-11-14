from pathlib import Path

from trashloop.analyze import analyze

RULE = "Always run the full unit test suite before opening a pull request and never skip failing tests."


def make(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def dups(report):
    return [f for f in report.findings if f.type == "duplicate"]


def test_exact_duplicate_across_files(tmp_path):
    root = make(tmp_path, {
        "CLAUDE.md": f"# A\n\n- {RULE}\n",
        "AGENTS.md": f"# B\n\n{RULE.upper()}\n",  # case/format differences normalize away
    })
    r = analyze(root)
    d = dups(r)
    assert len(d) == 1 and d[0].confidence == 1.0
    assert {e.file for e in d[0].evidence} == {"CLAUDE.md", "AGENTS.md"}
    assert r.metrics.est_tokens_duplicated > 0


def test_near_duplicate_with_wrapping_and_extra_words(tmp_path):
    a = "Never commit secrets, tokens or credentials to the repository because they leak through history."
    b = "Never commit secrets, tokens or credentials to the repository because they leak through history, even in forks."
    root = make(tmp_path, {"CLAUDE.md": f"# A\n\n{a}\n", ".claude/rules/sec.md": f"# S\n\n- {b}\n"})
    d = dups(analyze(root))
    assert len(d) == 1 and d[0].confidence < 1.0


def test_distinct_instructions_not_flagged(tmp_path):
    root = make(tmp_path, {
        "CLAUDE.md": "# A\n\nPrefer small pure functions and keep modules focused on a single responsibility each.\n",
        "AGENTS.md": "# B\n\nDocument every public endpoint in the OpenAPI file and keep examples synchronized with tests.\n",
    })
    assert dups(analyze(root)) == []


def test_docs_and_adrs_out_of_scope_and_short_lines_ignored(tmp_path):
    root = make(tmp_path, {
        "docs/a.md": f"{RULE}\n", "docs/b.md": f"{RULE}\n",  # kind DOC: not scoped
        "CLAUDE.md": "# A\n\n- Be nice.\n", "AGENTS.md": "# B\n\n- Be nice.\n",  # too short
    })
    assert dups(analyze(root)) == []
