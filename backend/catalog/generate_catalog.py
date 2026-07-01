#!/usr/bin/env python3
"""Convert ai_tool_feed.csv → catalog.json.

Run from the repo root:
    python backend/catalog/generate_catalog.py

Note: this rebuilds catalog.json from the feed. LLM-generated fields
(`formatted_description`, `compact_description`) are carried over from the
previous catalog.json per id, but ONLY when the source `description` is
unchanged (whitespace-normalised). When the feed's description actually
changed, the stale LLM text is dropped so the next LLM pass regenerates just
those items — a feed refresh therefore re-runs the LLM only for new/changed
products, not the whole assortment. After regenerating, re-run the LLM passes
(catalog/format_descriptions.py etc.) to fill the gaps.

Profile mapping:
  AI minimalist → A | AI ontdekker → B | AI planner → C
  must   → must_have_profiles
  should → should_have_profiles
  nice   → nice_to_have_profiles
  skip   → (omitted)
"""

import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend on path

# Shared with feed_diff.py so "stroller?" and "real description change?" are defined once.
from catalog.feed_lib import STROLLER_CATEGORIES, norm_desc as _norm_desc  # noqa: E402

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ai_tool_feed.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")

AVAILABILITY_MAP = {
    "in stock": "Op voorraad",
    "preorder": "Op bestelling",
}

PROFILE_COLUMNS = {
    "AI minimalist": "A",
    "AI ontdekker": "B",
    "AI planner": "C",
}


def extract_id(link: str) -> str:
    m = re.search(r"-(\d+)$", link.rstrip("/"))
    if m:
        return m.group(1)
    return re.sub(r"[^a-zA-Z0-9_-]", "_", link.split("/")[-1])


def parse_price(price_str: str) -> float:
    cleaned = price_str.replace("EUR", "").strip()
    return float(cleaned) if cleaned else 0.0


def build_profiles(row: dict) -> tuple[list[str], list[str], list[str]]:
    must, should, nice = [], [], []
    for col, profile_id in PROFILE_COLUMNS.items():
        val = row.get(col, "").strip().lower()
        if val == "must":
            must.append(profile_id)
        elif val == "should":
            should.append(profile_id)
        elif val == "nice":
            nice.append(profile_id)
    return must, should, nice


def convert_row(row: dict, is_stroller: bool) -> dict:
    item_id = (row.get("id") or "").strip() or extract_id(row["link"])
    must, should, nice = build_profiles(row)
    tags = [t.strip() for t in row.get("Product tags", "").split(",") if t.strip()]
    collection = row.get("Collection", "").strip() or None
    compatible_collections = [
        c.strip()
        for c in row.get("Compatibel met collectie", "").replace(";", ",").split(",")
        if c.strip()
    ]

    item = {
        "id": item_id,
        "group_id": (row.get("groep_id") or "").strip() or item_id,
        "name": row["title"].strip(),
        "brand": row["brand"].strip().lower(),
        "price": parse_price(row["price"]),
        "description": row["description"].strip(),
        "image_url": row["image_link"].strip(),
        "product_url": (row.get("link") or "").strip(),
        "availability": AVAILABILITY_MAP.get(row["availability"].strip(), row["availability"].strip()),
        "tags": tags,
        "collection": collection,
        "compatible_collections": compatible_collections,
        "must_have_profiles": must,
        "should_have_profiles": should,
        "nice_to_have_profiles": nice,
        "cross_sell_items": [],
    }

    if not is_stroller:
        item["type"] = "accessory"

    return item


# LLM-generated fields carried across a feed refresh (keyed by product id).
_CARRIED_LLM_FIELDS = ("formatted_description", "compact_description")


def _existing_llm_fields() -> dict:
    """Carry LLM-generated fields from a previous catalog.json so a feed refresh does
    not re-run the LLM passes for unchanged products.

    Returns {id: {"description": <source text it was derived from>, "fields": {...}}}.
    The source description is returned alongside so the caller can drop the carried
    fields when the feed's description actually changed."""
    if not os.path.exists(OUT_PATH):
        return {}
    with open(OUT_PATH, encoding="utf-8") as f:
        prev = json.load(f)
    out: dict = {}
    for s in prev.get("strollers", []):
        fields = {k: s[k] for k in _CARRIED_LLM_FIELDS if s.get(k)}
        if fields:
            out[s["id"]] = {"description": s.get("description", ""), "fields": fields}
    return out


def main() -> None:
    carried = _existing_llm_fields()

    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    strollers = []
    accessories = []
    refreshed = 0

    for row in rows:
        is_stroller = row["Categorie"] in STROLLER_CATEGORIES
        item = convert_row(row, is_stroller)
        if is_stroller:
            prev = carried.get(item["id"])
            if prev and _norm_desc(prev["description"]) == _norm_desc(item["description"]):
                item.update(prev["fields"])
            elif prev:
                # description changed → drop stale LLM text so the next pass regenerates it
                refreshed += 1
            strollers.append(item)
        else:
            accessories.append(item)

    catalog = {
        "version": "2.0-real",
        "note": "Generated from ai_tool_feed.csv — run generate_catalog.py to refresh",
        "strollers": strollers,
        "accessories": accessories,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    carried_kept = sum(1 for s in strollers if s.get("formatted_description"))
    print(f"Generated {OUT_PATH}")
    print(f"  strollers:   {len(strollers)}")
    print(f"  accessories: {len(accessories)}")
    print(f"  LLM text carried over: {carried_kept} strollers")
    print(f"  LLM text dropped (description changed): {refreshed} strollers → re-run LLM passes")


if __name__ == "__main__":
    main()
