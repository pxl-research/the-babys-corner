#!/usr/bin/env python3
"""Populate `formatted_description` (Markdown) for catalog strollers via the LLM.

The feed ships descriptions as delimiter-less walls of text. This pass asks the LLM
to reformat each one into Markdown (headings + bullets) without changing facts, and
writes it back into catalog.json under `formatted_description`. The frontend renders
that field as Markdown, falling back to the raw `description`.

Run AFTER generate_catalog.py (which rebuilds catalog.json from the feed and does not
carry this field). Requires an LLM provider in the environment, e.g.:

    cd backend && uv run --env-file ../.env python catalog/format_descriptions.py

Runs with bounded concurrency, a per-item timeout, and checkpoints catalog.json after
every item — so it is fast and safely resumable. Idempotent: skips strollers that
already have a non-empty `formatted_description` unless --force. Optional --limit N.
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm import format_description_markdown  # noqa: E402

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")


async def main(force: bool, limit: int | None, concurrency: int, item_timeout: float) -> None:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    strollers = data.get("strollers", [])
    todo = [s for s in strollers if force or not s.get("formatted_description")]
    if limit is not None:
        todo = todo[:limit]
    total = len(todo)
    print(f"Formatting {total} strollers (concurrency={concurrency}, timeout={item_timeout}s)…", flush=True)

    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    done = 0
    failed = 0

    async def write_catalog() -> None:
        with open(CATALOG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    async def worker(s: dict) -> None:
        nonlocal done, failed
        async with sem:
            try:
                md = await asyncio.wait_for(
                    format_description_markdown(s.get("name", ""), s.get("description", "")),
                    timeout=item_timeout,
                )
            except asyncio.TimeoutError:
                md = None
        if md:
            s["formatted_description"] = md
            async with write_lock:
                await write_catalog()  # checkpoint so a crash never loses progress
                done += 1
                print(f"  [{done + failed}/{total}] ok  {s['id']} {s.get('name', '')[:55]}", flush=True)
        else:
            async with write_lock:
                failed += 1
                print(f"  [{done + failed}/{total}] -- {s['id']} (no output / timeout)", flush=True)

    await asyncio.gather(*(worker(s) for s in todo))
    await write_catalog()
    print(f"Done. Formatted {done}/{total} ({failed} skipped). Catalog has {len(strollers)} strollers.", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-format even if already present")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N pending")
    ap.add_argument("--concurrency", type=int, default=6, help="parallel LLM calls")
    ap.add_argument("--timeout", type=float, default=60.0, help="per-item timeout (seconds)")
    args = ap.parse_args()
    asyncio.run(main(args.force, args.limit, args.concurrency, args.timeout))
