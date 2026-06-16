# AI feed refresh + variant collapse — implementation plan

Status: **implemented** (2026-06-16). This document records the analysis, the design
decisions, and the exact changes, so the work is reviewable and repeatable.

## 1. Goal

A new `ai_tool_feed.csv` arrived with extra columns. We need to:

1. Update the dataset **incrementally** — avoid re-running the expensive (LLM) scripts
   over the whole assortment when ~most of it is unchanged.
2. Understand and exploit the new columns where it genuinely helps.

## 2. What the new feed actually changed

Compared by `id` using a real CSV parser (not `wc -l` — descriptions contain embedded
newlines, so line counts lie).

### 2.1 Schema — three columns added, not two

| Column | Position | Meaning |
|---|---|---|
| `is_hoofdproduct_categorie` | **inserted** after `AI planner` (mid-row) | "is a main product (stroller/travel system), not an accessory" |
| `groep_id` | appended | variant-group key — same product in different colour/size |
| `gelinkte_templates` | appended | explicit list of linked variant template ids |

> Because `is_hoofdproduct_categorie` is inserted mid-row, any **positional** CSV parsing
> would silently misalign. `generate_catalog.py` uses name-based `csv.DictReader`, so it is
> safe. Keep it that way.

### 2.2 Rows added / removed (by id)

- old **587** rows → new **571** rows
- **29 added**, **45 removed**, **542 common** (net −16)
- ~92% of ids unchanged → the "99% the same" assumption holds for *identity*.

### 2.3 Content drift on the 542 common ids

| Field | Changed |
|---|---|
| `description` | 227 — but **135 whitespace/`&nbsp;`-only**, only **92 real** |
| `AI minimalist` / `AI planner` | 84 each |
| `sale_price` | 64 |
| `availability` | 20 |
| `price` | 4 |
| `title` | 6 |

Of the 92 real description changes, **33 are strollers** — the only ones that feed the
expensive per-item LLM passes.

## 3. The two new columns — investigation outcome

- **`groep_id`** — *confirmed* the hypothesis: it groups colour/size variants of one
  product (e.g. group `1093` = "Air layer autostoel groep 0+" in 7 colours). 340 groups,
  75 with >1 member. **Adopted** (see §5).
- **`gelinkte_templates`** — the unknown one. It is the explicit variant-link list and is a
  *superset* of the in-feed group members: for 275/309 populated rows it equals exactly the
  other members of its `groep_id` group, and the mismatches are references to variants
  **not in this feed** (discontinued / out-of-stock / filtered-out — some are in the
  *removed* set). Conclusion: authoritative but redundant with `groep_id` for in-catalog
  use. **Not wired in** (no value over `group_id` here; available in the raw feed if
  cross-feed variant linking is ever needed).
- **`is_hoofdproduct_categorie`** — `true` for 144 items, all strollers. Looked like a clean
  replacement for the hardcoded `STROLLER_CATEGORIES` set, but it is a strict subset that
  marks **3 genuine travel systems false** (`90252/90253/90254`, "Buggy/autostoel i",
  529 EUR). The category-based classifier is more correct. **Not adopted.**

## 4. Incremental dataset update

### 4.1 Pipeline (unchanged shape)

```
ai_tool_feed.csv → generate_catalog.py → catalog.json   (cheap, deterministic)
catalog.json → format_descriptions.py / generate_*_descriptions.py → LLM per stroller (expensive)
```

The LLM passes are **stroller-only** and **skip-if-present** (skip when
`formatted_description` / `compact_description` already set; `format_descriptions.py` has
`--force`).

### 4.2 Design: self-invalidating carry-over

`generate_catalog.py` rebuilds `catalog.json` from the feed and **carries the LLM-generated
fields over by id** — but only when the source `description` is **unchanged**
(whitespace-normalised). When the description actually changed, the stale LLM text is
dropped so the next LLM pass regenerates exactly those items.

Why normalise whitespace: the 135 trivial reflow/entity changes must **not** trigger a
regen; only the 92 real ones (33 strollers) should.

Effect on this refresh (verified by running it):

```
strollers:   147
accessories: 424
LLM text carried over: 88 strollers
LLM text dropped (description changed): 33 strollers → re-run LLM passes
```

New strollers (25) carry nothing, so total to regenerate ≈ **58 of 147** instead of all 147
(~60% saved). The mechanism is permanent — every future feed refresh re-runs the LLM only
for new/changed products.

### 4.3 Changes made

- `generate_catalog.py`
  - `_norm_desc()` helper (whitespace normalisation).
  - `_existing_formatted_descriptions()` → `_existing_llm_fields()`: now carries
    `formatted_description` **and** `compact_description`, returning each alongside the
    source `description` it was derived from.
  - `main()`: carry LLM fields only when `_norm_desc(prev) == _norm_desc(new)`, else drop;
    counts carried/dropped and prints them.
  - `convert_row()`: writes `group_id` (from `groep_id`, falls back to own id).
- Regenerated `backend/catalog/catalog.json`.

### 4.4 Operator step (still to run)

```bash
cd backend && uv run --env-file ../.env python catalog/format_descriptions.py
```

Skips the 88 carried strollers, regenerates the ~58 missing. Optionally skip the 33
trivial-edit regens by not running (they are cheap; running keeps text faithful).

## 5. Variant collapse (`group_id`)

### 5.1 Decision

Collapse **strollers** to one representative per `group_id` so the customer sees one card
per product, not one per colour. **Accessories are left ungrouped** — cross-sell already
de-dupes them by name (`_rank_by_color`).

Impact: stroller assortment **147 → 63** (28 multi-variant groups). This is a visible,
intended reduction.

### 5.2 Where

Single chokepoint: the whole recommendation engine reads strollers via
`CatalogService.get_all_strollers()` / `get_filtered_strollers()`. Collapse there → every
ranking/tier/batch path inherits it for free. `catalog.json` still stores **all** variants
(so `get_stroller(any colour id)` keeps working for favorites/shortlist).

### 5.3 Representative selection (deterministic)

Within a group, pick: **group leader** (`id == group_id`) → **available** → **lowest id**.
When filtering, the representative is chosen among the members that *survive* the filter,
so a filtered-out colour never represents the group.

### 5.4 Changes made

- `backend/app/services/catalog.py`
  - `_id_sort_key()`, `group_id_of()` helpers.
  - In `__init__`: build `self._variant_members` (group → member ids, available-first).
  - `_with_variants()` annotates a stroller (shallow copy) with `group_id`, `variant_ids`,
    `variant_count` — leaves the stored item pristine.
  - `_representative_id()`, `_collapse()`.
  - `get_stroller()` now returns the annotated copy; `get_all_strollers()` and the filtered
    path return collapsed lists.
- `backend/app/schemas.py` — `StrollerItem` gains optional `variant_count: int = 1` and
  `variant_ids: list[str] = []` (non-breaking).
- `backend/app/routers/session.py` — threads `variant_count` / `variant_ids` into the
  `StrollerItem` it builds.

### 5.5 Verified

```
strollers collapsed: 63
representatives with >1 variant: 28
biggest group rep: 138225 "Buggy ultracompact Aer² space black" variants=8
lookup non-rep variant 138230 -> group_id 138225, variant_count 8
accessories untouched: 424
```

## 6. Verification

- Full backend suite: **190 passed**.
- Unit tests build `CatalogService` without `group_id`; `group_id_of()` falls back to the
  item id, so each test item is its own group → no accidental merging.

> Note: the project `.venv` was broken (python symlink pointed at the old repo path
> `PXL/The Baby's Corner`, since moved under `02 - Instore AI-assistent/`). Repaired with
> `uv sync`. Run pytest via `env -u VIRTUAL_ENV uv run python -m pytest` if the stale
> `VIRTUAL_ENV` is still exported in the shell.

## 7. Files touched

- `ai_tool_feed.csv` (new feed)
- `backend/catalog/generate_catalog.py`
- `backend/catalog/catalog.json` (regenerated)
- `backend/app/services/catalog.py`
- `backend/app/schemas.py`
- `backend/app/routers/session.py`

## 7b. Reusable system for future feed updates

So future refreshes stay incremental by construction, not by hand:

- **`backend/catalog/feed_lib.py`** — single source of truth for the feed rules:
  `STROLLER_CATEGORIES`, `norm_desc()` (whitespace-normalised change detection),
  `is_stroller_row()`, and `diff_feeds()` (full by-id comparison → added/removed,
  per-field drift, real-vs-cosmetic description split, and the exact set of strollers the
  LLM passes will process). `generate_catalog.py` imports the same rules, so the preview
  and the actual carry-over can never disagree.
- **`backend/catalog/feed_diff.py`** — read-only CLI to preview a candidate feed's blast
  radius before applying it (`--new`, `--old`, `--json`).
- **`backend/tests/unit/test_feed_lib.py`** — regression guard: cosmetic description edits
  and accessory changes must never trigger LLM work; new/real-changed strollers must.
- **`docs/feed-update-runbook.md`** — the step-by-step operator procedure
  (preview → apply → fill LLM gaps → verify).

Verified the CLI reproduces the manual analysis exactly (29 added / 45 removed / 542
common, 92 real vs 135 cosmetic descriptions, 58 strollers needing LLM).

## 8. Follow-ups (not done)

- **Frontend colour-variant chip** — render "ook in N kleuren" using `variant_count` /
  `variant_ids`; optional colour picker that swaps to a sibling id. Data is already served.
- **Cross-sell colour matching** — representative carries one colour; acceptable today,
  revisit if colour-matched accessories regress.
- **Commit** — nothing committed yet; changes sit in the working tree.
