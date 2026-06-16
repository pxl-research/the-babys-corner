#!/usr/bin/env python3
"""Preview what a new ai_tool_feed.csv would change — BEFORE applying it.

Read-only. Compares a candidate feed against the current one (by product id) and
reports rows added/removed, schema changes, per-field content drift, and — most
importantly — exactly how many strollers the expensive LLM passes would (re)process.

Usage (from repo root or anywhere):

    python backend/catalog/feed_diff.py --new ~/Downloads/ai_tool_feed.csv
    python backend/catalog/feed_diff.py --new <path> --old <path> --json

Default --old is the feed currently committed at the repo root. Run this first, eyeball
the blast radius, then apply with generate_catalog.py.
"""

import argparse
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend on path

from catalog.feed_lib import diff_feeds, read_feed  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DEFAULT_OLD = os.path.join(REPO_ROOT, "ai_tool_feed.csv")


def _sample(ids: list[str], n: int = 15) -> str:
    head = ", ".join(ids[:n])
    return head + (f" … (+{len(ids) - n} more)" if len(ids) > n else "")


def main() -> None:
    ap = argparse.ArgumentParser(description="Preview an ai_tool_feed.csv update.")
    ap.add_argument("--new", required=True, help="candidate feed CSV")
    ap.add_argument("--old", default=DEFAULT_OLD, help="current feed CSV (default: repo root)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    old_rows, old_cols = read_feed(args.old)
    new_rows, new_cols = read_feed(args.new)
    d = diff_feeds(old_rows, new_rows, old_cols, new_cols)

    if args.json:
        import json
        print(json.dumps(asdict(d), ensure_ascii=False, indent=2))
        return

    print(f"old feed: {args.old}  ({d.old_count} rows)")
    print(f"new feed: {args.new}  ({d.new_count} rows)")
    print()
    if d.added_columns or d.removed_columns:
        print("SCHEMA:")
        if d.added_columns:
            print(f"  + added columns:   {', '.join(d.added_columns)}")
        if d.removed_columns:
            print(f"  - removed columns: {', '.join(d.removed_columns)}")
        print()
    print(f"rows: {len(d.added_ids)} added, {len(d.removed_ids)} removed, {d.common_count} common")
    if d.added_ids:
        print(f"  added ids:   {_sample(d.added_ids)}")
    if d.removed_ids:
        print(f"  removed ids: {_sample(d.removed_ids)}")
    print()
    print("content changes on common ids:")
    real = len(d.desc_real_changed)
    print(f"  description: {real} real, {d.desc_trivial_changed} cosmetic (ignored)")
    for f, c in d.field_changes.items():
        if f != "description":
            print(f"  {f}: {c}")
    print()
    changed_strollers = len(d.strollers_needing_llm) - len(d.new_strollers)
    print("LLM impact (strollers only — the expensive passes):")
    print(f"  new strollers:            {len(d.new_strollers)}")
    print(f"  changed-description:      {changed_strollers}")
    print(f"  → strollers needing LLM:  {len(d.strollers_needing_llm)}  {_sample(d.strollers_needing_llm)}")
    print(f"  removed strollers:        {len(d.removed_strollers)}")
    print()
    print("Apply with:  python backend/catalog/generate_catalog.py")


if __name__ == "__main__":
    main()
