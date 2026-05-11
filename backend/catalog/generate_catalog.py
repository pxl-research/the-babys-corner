#!/usr/bin/env python3
"""Convert ai_tool_feed.csv → catalog.json.

Run from the repo root:
    python backend/catalog/generate_catalog.py

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

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ai_tool_feed.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")

STROLLER_CATEGORIES = {
    "op stap / 2-in-1 reissysteem: autostoel kinderwagen buggy",
    "op stap / buggy's / buggy's",
    "op stap / kinderwagens / kinderwagens",
    "op stap / kinderwagens en buggy's / kinderwagens en buggy's vr 2",
    "op stap / kinderwagens en buggy's / kinderkar",
}

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
    item_id = extract_id(row["link"])
    must, should, nice = build_profiles(row)

    item = {
        "id": item_id,
        "name": row["title"].strip(),
        "brand": row["brand"].strip().lower(),
        "price": parse_price(row["price"]),
        "description": row["description"].strip(),
        "image_url": row["image_link"].strip(),
        "availability": AVAILABILITY_MAP.get(row["availability"].strip(), row["availability"].strip()),
        "must_have_profiles": must,
        "should_have_profiles": should,
        "nice_to_have_profiles": nice,
        "cross_sell_items": [],
    }

    if not is_stroller:
        item["type"] = "accessory"

    return item


def main() -> None:
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    strollers = []
    accessories = []

    for row in rows:
        is_stroller = row["Categorie"] in STROLLER_CATEGORIES
        item = convert_row(row, is_stroller)
        if is_stroller:
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

    print(f"Generated {OUT_PATH}")
    print(f"  strollers:   {len(strollers)}")
    print(f"  accessories: {len(accessories)}")


if __name__ == "__main__":
    main()
