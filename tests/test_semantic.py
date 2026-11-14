from pathlib import Path

from trashloop.analyze import analyze
from trashloop.analyzers.scope import overlaps, scope_of
from trashloop.llm.client import FakeJudge

A = "Always use tabs for indentation in all source files across the repository."
B = "Never use tabs for indentation in source files, always use four spaces across the repository."


def make(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def test_no_judge_means_no_llm_findings(tmp_path):
    root = make(tmp_path, {"CLAUDE.md": f"# A\n\n{A}\n", "AGENTS.md": f"# B\n\n{B}\n"})
    assert [f for f in analyze(root).findings if f.method == "llm"] == []


def test_conflict_found_via_judge_on_candidate_pair(tmp_path):
    root = make(tmp_path, {"CLAUDE.md": f"# A\n\n{A}\n", "AGENTS.md": f"# B\n\n{B}\n"})
    judge = FakeJudge({"Never use tabs": "conflict"})
    r = analyze(root, judge=judge)
    c = [f for f in r.findings if f.type == "conflict"]
    assert len(c) == 1 and c[0].method == "llm" and len(c[0].evidence) == 2
    assert r.metrics.llm_input_tokens > 0


def test_unrelated_text_never_reaches_judge(tmp_path):
    root = make(tmp_path, {
        "CLAUDE.md": "# A\n\nPrefer small pure functions and keep modules focused on a single responsibility each.\n",
        "AGENTS.md": "# B\n\nDocument every public endpoint in the OpenAPI file and keep examples synchronized with tests.\n",
    })
    judge = FakeJudge(default="conflict")
    analyze(root, judge=judge)
    assert judge.calls == 0


def test_max_pairs_caps_llm_calls(tmp_path):
    lines = "\n\n".join(f"Always format the module number{i} configuration files with the standard formatter tool." for i in range(10))
    root = make(tmp_path, {"CLAUDE.md": f"# A\n\n{lines}\n", "AGENTS.md": f"# B\n\n{lines.replace('Always', 'Never')}\n"})
    judge = FakeJudge(default="compatible")
    analyze(root, judge=judge, max_llm_pairs=5)
    assert judge.calls <= 5


def test_scope_disjoint_rules_do_not_overlap():
    py = scope_of(".claude/rules/py.md", '---\npaths:\n  - "src/py/**"\n---\nx', False)
    ts = scope_of(".claude/rules/ts.md", '---\npaths:\n  - "src/ts/**"\n---\nx', False)
    glob = scope_of("CLAUDE.md", "# x", True)
    assert not overlaps(py, ts) and overlaps(py, glob)
