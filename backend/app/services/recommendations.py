from app.services.catalog import CatalogService, is_available
import random
import re
from itertools import groupby

_COLOR_ALIASES = {
    "black": "black",
    "zwart": "black",
    "rich black": "black",
    "nitro black": "black",
    "grey": "grey",
    "gray": "grey",
    "grijs": "grey",
    "graphite": "grey",
    "moon grey": "grey",
    "beige": "beige",
    "taupe": "taupe",
    "desert taupe": "taupe",
    "green": "green",
    "groen": "green",
    "sage": "green",
    "olive": "green",
    "blue": "blue",
    "blauw": "blue",
    "navy": "blue",
    "pink": "pink",
    "roze": "pink",
    "brown": "brown",
    "bruin": "brown",
    "white": "white",
    "wit": "white",
    "sand": "sand",
    "clay": "clay",
    "khaki": "khaki",
    "mint": "mint",
    "amber": "amber",
    "orange": "orange",
    "yellow": "yellow",
    "red": "red",
    "antraciet": "anthracite",
    "anthracite": "anthracite",
}


def _tier(stroller: dict, profile: str) -> int:
    if profile in stroller.get("must_have_profiles", []):
        return 0
    if profile in stroller.get("should_have_profiles", []):
        return 1
    if profile in stroller.get("nice_to_have_profiles", []):
        return 2
    return 3


def compute_first_nine(profile: str, catalog: CatalogService) -> list[dict]:
    strollers = catalog.get_all_strollers()
    strollers_sorted = sorted(
        strollers,
        key=lambda s: (_tier(s, profile), 0 if is_available(s) else 1),
    )
    return _shuffle_within_equal_groups(
        strollers_sorted,
        key_fn=lambda s: (_tier(s, profile), 0 if is_available(s) else 1),
    )[:9]


def _shuffle_within_equal_groups(items: list, key_fn) -> list:
    shuffled: list = []
    for _, group in groupby(items, key=key_fn):
        block = list(group)
        random.shuffle(block)
        shuffled.extend(block)
    return shuffled


def diversify_llm_order(
    ordered_ids: list[str],
    profile: str,
    catalog: CatalogService,
    keep_top_n: int = 1,
) -> list[str]:
    if len(ordered_ids) <= keep_top_n:
        return ordered_ids
    prefix = ordered_ids[:keep_top_n]
    tail = ordered_ids[keep_top_n:]

    def key_for(id_: str) -> tuple[int, int]:
        stroller = catalog.get_stroller(id_)
        if not stroller:
            return (99, 99)
        return (_tier(stroller, profile), 0 if is_available(stroller) else 1)

    # Shuffle equal-rank items globally in the tail (not only contiguous groups),
    # then place them back into their original rank slots to keep overall pattern.
    slots_by_key: dict[tuple[int, int], list[int]] = {}
    ids_by_key: dict[tuple[int, int], list[str]] = {}
    for idx, id_ in enumerate(tail):
        key = key_for(id_)
        slots_by_key.setdefault(key, []).append(idx)
        ids_by_key.setdefault(key, []).append(id_)

    diversified_tail = tail[:]
    for key, ids in ids_by_key.items():
        shuffled = ids[:]
        random.shuffle(shuffled)
        for slot, id_ in zip(slots_by_key[key], shuffled):
            diversified_tail[slot] = id_

    return prefix + diversified_tail


def compute_filtered_order(
    catalog: CatalogService,
    profile: str | None = None,
    tags: list[str] | None = None,
    brands: list[str] | None = None,
    collections: list[dict] | None = None,
    tag_match: str = "any",
) -> list[str]:
    """Return filtered stroller IDs, diversified within equal-rank groups."""
    strollers = catalog.get_filtered_strollers(tags, brands, collections, tag_match)

    # Rank by profile tier (when known) then availability; only the key differs.
    if profile:
        def key_fn(s):
            return (_tier(s, profile), 0 if is_available(s) else 1)
    else:
        def key_fn(s):
            return (0 if is_available(s) else 1)

    diversified = _shuffle_within_equal_groups(sorted(strollers, key=key_fn), key_fn=key_fn)
    return [s["id"] for s in diversified]


def compute_progressive_tag_order(
    catalog: CatalogService,
    profile: str | None,
    tags: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """AND across all selected tags; if that yields zero strollers, drop tags one at a
    time until matches remain (progressive relaxation).

    Each drop removes the single tag whose removal recovers the most matches (greedy).
    Ties keep the earlier tag, so higher-priority wishes (asked first) survive longest.
    Returns (reco_order, kept_tags, dropped_tags). If every tag is dropped, falls back to
    the profile-ranked full assortment.
    """
    remaining = list(tags)
    dropped: list[str] = []
    while remaining:
        order = compute_filtered_order(catalog, profile, remaining, tag_match="all")
        if order:
            return order, remaining, dropped
        best_tag = remaining[0]
        best_count = -1
        for t in remaining:
            subset = [x for x in remaining if x != t]
            count = len(catalog.get_filtered_strollers(subset or None, tag_match="all"))
            if count > best_count:
                best_count = count
                best_tag = t
        dropped.append(best_tag)
        remaining.remove(best_tag)
    return compute_filtered_order(catalog, profile), [], dropped


def get_batch(
    batch_num: int,
    reco_order: list[str],
    accessory_favorites: list[str],
    catalog: CatalogService,
    stroller_favorites: list[str] | None = None,
    extra_reco_order: list[str] | None = None,
) -> list[dict]:
    start = (batch_num - 1) * 3
    end = start + 3

    if batch_num <= 3:
        batch_ids = reco_order[start:end]
        return [s for id_ in batch_ids if (s := catalog.get_stroller(id_))]

    # Batch 4+: prefer items beyond position 9 in reco_order (filter-generated full order);
    # fall back to catalog remainder when reco_order has only 9 entries (quiz-generated).
    remaining_from_reco = reco_order[9:]
    if remaining_from_reco:
        remaining = remaining_from_reco
    else:
        shown_ids = set(reco_order)
        all_ids = [s["id"] for s in catalog.get_all_strollers()]
        remaining = [id_ for id_ in all_ids if id_ not in shown_ids]

    if extra_reco_order:
        remaining_set = set(remaining)
        remaining = [id_ for id_ in extra_reco_order if id_ in remaining_set]

    extra_start = (batch_num - 4) * 3
    batch_ids = remaining[extra_start:extra_start + 3]
    return [s for id_ in batch_ids if (s := catalog.get_stroller(id_))]


# How many cross-sell accessories to surface, scaled by profile appetite.
_CROSS_SELL_TARGET = {"A": 5, "B": 10, "C": 15}


def _accessory_collections(accessory: dict) -> set[str]:
    colls = {c for c in (accessory.get("compatible_collections") or []) if c}
    own = (accessory.get("collection") or "").strip()
    if own:
        colls.add(own)
    return colls


def get_cross_sell_items(
    stroller: dict,
    profile: str,
    catalog: CatalogService,
) -> list[dict]:
    """Accessories compatible with the stroller's collection only.

    An accessory matches when the stroller's collection appears in its
    `compatible_collections` (or equals its own collection). Strollers whose
    collection has no compatible accessory show none — this is intentional;
    cross-sell is strictly collection-scoped, not a heuristic.
    """
    collection = (stroller.get("collection") or "").strip()
    if not collection:
        return []

    pool = [a for a in catalog.get_all_accessories() if collection in _accessory_collections(a)]
    if not pool:
        return []

    target_total = _CROSS_SELL_TARGET.get(profile, _CROSS_SELL_TARGET["B"])
    stroller_colors = _extract_colors(stroller.get("name", ""))

    def normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (name or "").lower())

    # Colour-matching accessories first, then the rest; shuffle within each group.
    rng = random.Random()
    if stroller_colors:
        color_matches = [a for a in pool if _extract_colors(a.get("name", "")) & stroller_colors]
        rest = [a for a in pool if a not in color_matches]
    else:
        color_matches, rest = [], pool[:]
    rng.shuffle(color_matches)
    rng.shuffle(rest)

    selected: list[dict] = []
    seen_names: set[str] = set()
    for acc in color_matches + rest:
        norm = normalize_name(acc.get("name", ""))
        if norm in seen_names:
            continue
        seen_names.add(norm)
        selected.append(acc)
        if len(selected) == target_total:
            break
    return selected


def _extract_colors(name: str) -> set[str]:
    lowered = (name or "").lower()
    colors: set[str] = set()
    for token, canonical in _COLOR_ALIASES.items():
        if token in lowered:
            colors.add(canonical)
    return colors
