# Runbook: updating `ai_tool_feed.csv`

How to apply a new product feed without re-doing work on products that didn't change.

## TL;DR

```bash
# 1. Preview the blast radius (read-only, changes nothing)
python backend/catalog/feed_diff.py --new ~/Downloads/ai_tool_feed.csv

# 2. Apply: replace the feed and rebuild the catalog
cp ~/Downloads/ai_tool_feed.csv ai_tool_feed.csv
python backend/catalog/generate_catalog.py

# 3. Fill only the LLM gaps (new + changed-description strollers)
cd backend && uv run --env-file ../.env python catalog/format_descriptions.py

# 4. Verify
cd backend && uv run python -m pytest -q
```

## Why this is incremental (the design)

The cost in this pipeline is the **LLM passes**, and they only run on **strollers**.
Everything is built so they touch the fewest products possible:

- `generate_catalog.py` rebuilds `catalog.json` but **carries over** the LLM-generated
  fields (`formatted_description`, `compact_description`) from the previous
  `catalog.json`, keyed by product id — *only if the source `description` is unchanged*.
- "Unchanged" is judged **after whitespace normalisation** (`feed_lib.norm_desc`), so
  cosmetic reflows / `&nbsp;` cleanups don't trigger regeneration.
- When a description really changed, the stale LLM text is dropped, so the next LLM pass
  regenerates *exactly* those items (the passes skip any item that already has the field).
- New products have no carried text → regenerated. Removed products simply vanish.

Net: a refresh re-runs the LLM only for **new strollers + strollers with a real
description change**. Everything else is reused for free.

The "is it a stroller?" and "did the description really change?" rules live in **one
place** — `backend/catalog/feed_lib.py` — and are shared by both the generator and the
preview tool, so the preview's LLM count always matches what the generator will do.

## Step 1 — preview (`feed_diff.py`)

Read-only. Compares the candidate feed against the currently committed one (by id) and
prints:

- schema changes (added/removed columns)
- rows added / removed / common
- per-field content drift on common ids (description split into **real** vs **cosmetic**)
- **LLM impact**: new strollers, changed-description strollers, total strollers needing LLM

```bash
python backend/catalog/feed_diff.py --new <path>            # vs committed feed
python backend/catalog/feed_diff.py --new <path> --old <path>
python backend/catalog/feed_diff.py --new <path> --json     # machine-readable
```

Use it to sanity-check before applying — e.g. if "strollers needing LLM" is unexpectedly
large, look at why before spending the LLM budget. A schema change will show every common
id as "changed" for the new column (expected, harmless).

## Step 2 — apply (`generate_catalog.py`)

```bash
cp <new feed> ai_tool_feed.csv
python backend/catalog/generate_catalog.py
```

It prints how many strollers' LLM text was carried over vs dropped. Idempotent: running it
twice carries the same set the second time (nothing left to drop).

It also writes `group_id` on every item; the runtime collapses stroller colour/size
variants to one representative per group (see the variant-collapse plan).

## Step 3 — fill LLM gaps

```bash
cd backend && uv run --env-file ../.env python catalog/format_descriptions.py
# (and generate_compact_descriptions.py if compact_description is in use)
```

These skip any stroller that already has the field, so only the gaps from step 2 are
processed. `format_descriptions.py --force` regenerates everything (rarely needed).

To deliberately **skip** trivial-but-real description changes, you can choose not to run
these for those ids — but they are cheap and keep the text faithful to the feed.

## Step 4 — verify

```bash
cd backend && uv run python -m pytest -q
```

`tests/unit/test_feed_lib.py` is the regression guard for the incremental rule: cosmetic
edits and accessory changes must never produce LLM work.

## Gotchas

- **Never positionally parse the feed.** Columns can be inserted mid-row (e.g.
  `is_hoofdproduct_categorie` was). Always parse by name (`csv.DictReader`).
- **`.venv` path.** If the repo was moved, the venv may hold a stale absolute path. Repair
  with `uv sync`; run pytest as `env -u VIRTUAL_ENV uv run python -m pytest` if a stale
  `VIRTUAL_ENV` is exported.
- `catalog.json` stores **all** variants (not collapsed) so favorites/shortlist by any
  colour id keep resolving; collapsing happens only at serving time.
