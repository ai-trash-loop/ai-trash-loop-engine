from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trashloop.analyze import analyze


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="trashloop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="Analyze a local repository checkout")
    a.add_argument("path", type=Path)
    a.add_argument("--out", type=Path, help="Write JSON report here (default: stdout)")
    a.add_argument("--llm", action="store_true", help="Judge candidate pairs with an LLM (needs ANTHROPIC_API_KEY; costs money)")
    a.add_argument("--model", default="claude-haiku-5-5")
    a.add_argument("--max-llm-pairs", type=int, default=50, help="Hard cap on LLM-judged pairs")
    a.add_argument("--cache-dir", type=Path, default=Path(".llm_cache"))
    args = ap.parse_args(argv)
    if not args.path.is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 2
    judge = None
    if args.llm:
        from trashloop.llm.client import AnthropicJudge

        judge = AnthropicJudge(model=args.model, cache_dir=args.cache_dir)
    js = analyze(args.path, judge=judge, max_llm_pairs=args.max_llm_pairs).model_dump_json(indent=2)
    if args.out:
        args.out.write_text(js + "\n")
    else:
        print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
