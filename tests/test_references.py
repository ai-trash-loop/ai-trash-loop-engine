from pathlib import Path

from trashloop.analyze import analyze


def make(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def refs(report):
    return [f for f in report.findings if f.type == "broken_reference"]


def test_broken_and_valid_links(tmp_path):
    root = make(tmp_path, {
        "CLAUDE.md": "# Guide\n\nSee [rules](docs/rules.md) and [missing](docs/nope.md).\n",
        "docs/rules.md": "# Rules\n\n## Naming\n\nBack to [guide](../CLAUDE.md#guide).\n",
    })
    r = analyze(root)
    found = refs(r)
    assert len(found) == 1
    e = found[0].evidence[0]
    assert (e.file, e.line_start) == ("CLAUDE.md", 3)
    assert "nope.md" in found[0].summary


def test_bad_anchor_flagged_good_anchor_ok(tmp_path):
    root = make(tmp_path, {
        "a.md": "# A\n\n[ok](b.md#naming) [bad](b.md#missing)\n",
        "b.md": "# B\n\n## Naming\n",
    })
    found = refs(analyze(root))
    assert len(found) == 1 and "#missing" in found[0].summary


def test_ignores_external_code_blocks_and_templates(tmp_path):
    root = make(tmp_path, {
        "a.md": "[web](https://example.com/x)\n\n```\n[fake](nothing.md)\n```\n\n[tpl](docs/{name}.md)\n",
    })
    assert refs(analyze(root)) == []


def test_empty_repo_has_no_findings(tmp_path):
    r = analyze(tmp_path)
    assert r.context_files == [] and r.findings == []


def test_html_anchor_and_build_dir_targets(tmp_path):
    root = make(tmp_path, {
        "a.md": '[x](b.md#cli-1) [y](build/real.props)\n',
        "b.md": '# B\n\n<a id="cli-1"></a>\n',
        "build/real.props": "x",
    })
    assert refs(analyze(root)) == []


def test_stale_code_span_paths(tmp_path):
    root = make(tmp_path, {
        "CLAUDE.md": "See `src/app/main.py` and `src/gone/old.py`, plus `/usr/bin/env` and `*.md` and `README.md`.\n",
        "src/app/main.py": "x", "README.md": "# r\n",
    })
    stale = [f for f in analyze(root).findings if f.type == "stale"]
    assert len(stale) == 1 and "src/gone/old.py" in stale[0].summary


def test_stale_skips_changelog_placeholders_and_examples(tmp_path):
    root = make(tmp_path, {
        "src/a.py": "x",
        "CHANGELOG.md": "Removed `src/old/gone.py`.\n",
        "CLAUDE.md": "Pages live in `src/docs/JDxxx.md`, e.g. `src/missing/example.md`.\n",
    })
    assert [f for f in analyze(root).findings if f.type == "stale"] == []


def test_anchor_matching_tolerates_diacritics_and_trailing_hyphen(tmp_path):
    root = make(tmp_path, {
        "a.md": "[x](b.md#ajouter-vous-meme) [y](b.md#quest-ce-quun-dummy) [z](b.md#really-missing)\n",
        "b.md": "# B\n\n## Ajouter vous-même\n\n## Qu'est-ce qu'un dummy ?\n",
    })
    found = refs(analyze(root))
    assert len(found) == 1 and "really-missing" in found[0].summary


def test_stale_skips_historical_statements_and_ellipsis(tmp_path):
    root = make(tmp_path, {
        "src/a.py": "x",
        "CLAUDE.md": "`src/old/tool` was not ported. Links point to `src/docs/...` here.\n",
    })
    assert [f for f in analyze(root).findings if f.type == "stale"] == []
