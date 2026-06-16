"""Shared feed primitives for the catalog pipeline.

Single source of truth for: how a row is classified as a stroller, how a description
is normalised for change-detection, and how two feeds are diffed. Both
``generate_catalog.py`` (which decides what LLM text to carry over) and
``feed_diff.py`` (which previews a candidate feed) import from here, so the
"what counts as a real change" rule is defined in exactly one place.
"""

import csv
import re
from dataclasses import dataclass, field

# Categories whose products are full strollers / travel systems (everything else is an
# accessory). Kept here so generate_catalog.py and the diff tool agree.
STROLLER_CATEGORIES = {
    "op stap / 2-in-1 reissysteem: autostoel kinderwagen buggy",
    "op stap / kinderwagens en buggy's / complete sets",
}


def norm_desc(s: str) -> str:
    """Whitespace-normalised description.

    Trivial reflows and HTML-entity cleanups (e.g. ``&nbsp;`` → space, added newlines)
    collapse to the same string, so they are NOT treated as a real change. Only this
    rule decides whether LLM-derived text must be regenerated — keep it identical on
    both the generate and diff sides.
    """
    return re.sub(r"\s+", " ", (s or "").strip())


def is_stroller_row(row: dict) -> bool:
    return row.get("Categorie") in STROLLER_CATEGORIES


def read_feed(path: str) -> tuple[list[dict], list[str]]:
    """Return (rows, column_names) from a feed CSV."""
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


# Fields worth reporting on for common ids. `description` is handled separately
# (real vs trivial); the rest are plain equality.
_TRACKED_FIELDS = (
    "title", "price", "sale_price", "availability",
    "AI minimalist", "AI ontdekker", "AI planner",
    "Product tags", "Categorie", "Collection",
    "accessoire_ids", "alternatief_ids", "groep_id", "gelinkte_templates",
)


@dataclass
class FeedDiff:
    old_count: int
    new_count: int
    added_ids: list[str]
    removed_ids: list[str]
    common_count: int
    added_columns: list[str]
    removed_columns: list[str]
    field_changes: dict[str, int]          # field -> # of common ids that changed
    desc_real_changed: list[str]           # common ids whose description really changed
    desc_trivial_changed: int              # common ids whose description changed only cosmetically
    strollers_needing_llm: list[str] = field(default_factory=list)
    new_strollers: list[str] = field(default_factory=list)
    removed_strollers: list[str] = field(default_factory=list)


def diff_feeds(
    old_rows: list[dict],
    new_rows: list[dict],
    old_columns: list[str] | None = None,
    new_columns: list[str] | None = None,
) -> FeedDiff:
    """Compare two feeds by ``id`` and report the blast radius of switching to ``new``.

    ``strollers_needing_llm`` is the set the expensive LLM passes will (re)process:
    every new stroller plus every common stroller whose description really changed.
    This mirrors generate_catalog.py's carry-over rule exactly.
    """
    old = {r["id"]: r for r in old_rows}
    new = {r["id"]: r for r in new_rows}
    old_ids, new_ids = set(old), set(new)
    common = old_ids & new_ids

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)

    field_changes: dict[str, int] = {}
    desc_real: list[str] = []
    desc_trivial = 0
    for i in sorted(common):
        o, n = old[i], new[i]
        for f in _TRACKED_FIELDS:
            if (o.get(f) or "").strip() != (n.get(f) or "").strip():
                field_changes[f] = field_changes.get(f, 0) + 1
        od, nd = o.get("description", ""), n.get("description", "")
        if od.strip() != nd.strip():
            if norm_desc(od) == norm_desc(nd):
                desc_trivial += 1
            else:
                desc_real.append(i)

    new_strollers = sorted(i for i in added if is_stroller_row(new[i]))
    removed_strollers = sorted(i for i in removed if is_stroller_row(old[i]))
    real_changed_strollers = [i for i in desc_real if is_stroller_row(new[i])]
    needs_llm = sorted(set(new_strollers) | set(real_changed_strollers))

    oc = set(old_columns or [])
    nc = set(new_columns or [])

    return FeedDiff(
        old_count=len(old_rows),
        new_count=len(new_rows),
        added_ids=added,
        removed_ids=removed,
        common_count=len(common),
        added_columns=sorted(nc - oc),
        removed_columns=sorted(oc - nc),
        field_changes=dict(sorted(field_changes.items(), key=lambda kv: -kv[1])),
        desc_real_changed=desc_real,
        desc_trivial_changed=desc_trivial,
        strollers_needing_llm=needs_llm,
        new_strollers=new_strollers,
        removed_strollers=removed_strollers,
    )
