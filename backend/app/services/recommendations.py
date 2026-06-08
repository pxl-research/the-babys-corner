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


# Wishes we protect during relaxation: these are dropped only when no other tag is
# left to drop, so a duo/twin or from-birth requirement survives above all others.
PRIORITY_TAGS = frozenset({"Twee kinderen (Duo / Tweeling)", "0m+"})


def compute_progressive_tag_order(
    catalog: CatalogService,
    profile: str | None,
    tags: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """AND across all selected tags; if that yields zero strollers, drop tags one at a
    time until matches remain (progressive relaxation).

    Each drop removes the single tag whose removal recovers the most matches (greedy).
    Priority tags (PRIORITY_TAGS) are held back: a priority tag is only dropped once no
    non-priority tag remains, so requirements like duo/twin or from-birth survive longest.
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
        # Relax non-priority tags first; only touch priority tags when nothing else is left.
        droppable = [t for t in remaining if t not in PRIORITY_TAGS] or remaining
        best_tag = droppable[0]
        best_count = -1
        for t in droppable:
            subset = [x for x in remaining if x != t]
            count = len(catalog.get_filtered_strollers(subset or None, tag_match="all"))
            if count > best_count:
                best_count = count
                best_tag = t
        dropped.append(best_tag)
        remaining.remove(best_tag)
    return compute_filtered_order(catalog, profile), [], dropped


def _greedy_drop_tag(catalog: CatalogService, remaining: list[str]) -> str:
    """Pick the next tag to relax: a non-priority tag if any remain, else a priority one.
    Among candidates, drop the one whose removal recovers the most matches (greedy)."""
    droppable = [t for t in remaining if t not in PRIORITY_TAGS] or remaining
    best_tag, best_count = droppable[0], -1
    for t in droppable:
        subset = [x for x in remaining if x != t]
        count = len(catalog.get_filtered_strollers(subset or None, tag_match="all"))
        if count > best_count:
            best_count = count
            best_tag = t
    return best_tag


def _tier_label(displayed_index: int, exact_present: bool, no_tags: bool) -> str:
    """Generic, customer-safe heading per tier (never names the hidden tags)."""
    if no_tags:
        return "Onze aanbevelingen"
    if displayed_index == 0:
        return "Exacte matches" if exact_present else "Beste matches"
    if displayed_index == 1:
        return "Ruimere selectie die goed bij jullie past"
    return "Nog ruimere opties"


def compute_tiered_tag_order(
    catalog: CatalogService,
    profile: str | None,
    tags: list[str],
) -> tuple[list[str], list[dict], list[str]]:
    """Layer strollers from exact match to progressively relaxed selections.

    Tier 0 is the strict AND of all selected tags. Each later tier relaxes one more
    tag (priority tags last, greedy by recovery) and contains only the strollers it
    newly unlocks. Tiers that unlock nothing are skipped. Relaxation continues until
    every tag is dropped, so the deepest tier mops up the rest of the assortment.

    Returns (reco_order, tiers, primary_kept):
      - reco_order: flat list of stroller IDs, tier 0 first.
      - tiers: list of {label, start, count} segmenting reco_order for headings.
      - primary_kept: the tag set of the first non-empty tier (for accessory filtering).
    """
    remaining = list(tags)
    dropped: list[str] = []
    seen: set[str] = set()
    reco_order: list[str] = []
    raw_tiers: list[dict] = []
    primary_kept: list[str] | None = None

    while True:
        order = compute_filtered_order(catalog, profile, remaining or None, tag_match="all")
        new_ids = [i for i in order if i not in seen]
        if new_ids:
            if primary_kept is None:
                primary_kept = list(remaining)
            start = len(reco_order)
            reco_order.extend(new_ids)
            seen.update(new_ids)
            raw_tiers.append({"dropped": list(dropped), "start": start, "count": len(new_ids)})
        if not remaining:
            break
        tag = _greedy_drop_tag(catalog, remaining)
        dropped.append(tag)
        remaining.remove(tag)

    no_tags = not tags
    exact_present = bool(raw_tiers) and not raw_tiers[0]["dropped"]
    tiers = [
        {"label": _tier_label(d, exact_present, no_tags), "start": t["start"], "count": t["count"]}
        for d, t in enumerate(raw_tiers)
    ]
    return reco_order, tiers, (primary_kept or [])


def reorder_within_tiers(
    reco_order: list[str], tiers: list[dict], new_order: list[str]
) -> tuple[list[str], list[dict]]:
    """After a global reorder (e.g. note rerank), re-segment so tier boundaries hold.

    `new_order` is a permutation of `reco_order`. Each ID keeps its original tier and
    the tiers' sizes are unchanged, so IDs are stably regrouped by tier and only the
    start indices are recomputed. Returns (ordered_ids, rebuilt_tiers).
    """
    rank_of: dict[str, int] = {}
    for rank, tier in enumerate(tiers):
        for id_ in reco_order[tier["start"]:tier["start"] + tier["count"]]:
            rank_of[id_] = rank
    ordered = sorted(new_order, key=lambda id_: rank_of.get(id_, len(tiers)))
    rebuilt, cursor = [], 0
    for tier in tiers:
        rebuilt.append({"label": tier["label"], "start": cursor, "count": tier["count"]})
        cursor += tier["count"]
    return ordered, rebuilt


# Strollers shown per batch on the results page. Sized for comfortable browsing
# (fills a 3-column grid). PRIMARY_POOL is the count of leading reco_order picks
# (see compute_first_nine) served before the relaxed/remaining assortment and
# favorites adaptation kick in; PRIMARY_BATCHES is how many batches that pool spans.
BATCH_SIZE = 9
PRIMARY_POOL = 9
PRIMARY_BATCHES = PRIMARY_POOL // BATCH_SIZE


def get_batch(
    batch_num: int,
    reco_order: list[str],
    accessory_favorites: list[str],
    catalog: CatalogService,
    stroller_favorites: list[str] | None = None,
    extra_reco_order: list[str] | None = None,
) -> list[dict]:
    start = (batch_num - 1) * BATCH_SIZE
    end = start + BATCH_SIZE

    # Primary pool: leading PRIMARY_POOL picks of reco_order, served first.
    if start < PRIMARY_POOL:
        batch_ids = reco_order[start:min(end, PRIMARY_POOL)]
        return [s for id_ in batch_ids if (s := catalog.get_stroller(id_))]

    # Beyond the primary pool: prefer the relaxed tail of reco_order (filter-generated
    # full order); fall back to catalog remainder when reco_order holds only the
    # primary pool (quiz-generated).
    remaining_from_reco = reco_order[PRIMARY_POOL:]
    if remaining_from_reco:
        remaining = remaining_from_reco
    else:
        shown_ids = set(reco_order)
        all_ids = [s["id"] for s in catalog.get_all_strollers()]
        remaining = [id_ for id_ in all_ids if id_ not in shown_ids]

    if extra_reco_order:
        remaining_set = set(remaining)
        remaining = [id_ for id_ in extra_reco_order if id_ in remaining_set]

    extra_start = start - PRIMARY_POOL
    batch_ids = remaining[extra_start:extra_start + BATCH_SIZE]
    return [s for id_ in batch_ids if (s := catalog.get_stroller(id_))]


# Cross-sell composition per profile: how many accessories to draw from each profile
# category. Caps are the row sums (A=5, B=10, C=15). Untagged accessories are never
# shown, and categories absent for a profile are excluded entirely:
#   A (Minimalist): must-only.
#   B (Ontdekker):  mostly must, a few should.
#   C (Planner):    even mix of must, should and nice.
# When a category has fewer items than its quota, the shortfall is redistributed to the
# profile's other allowed categories in priority order (must > should > nice).
_CROSS_SELL_QUOTA: dict[str, dict[str, int]] = {
    "A": {"must": 5},
    "B": {"must": 7, "should": 3},
    "C": {"must": 5, "should": 5, "nice": 5},
}

_TIER_CATEGORY = {0: "must", 1: "should", 2: "nice"}


def _accessory_collections(accessory: dict) -> set[str]:
    colls = {c for c in (accessory.get("compatible_collections") or []) if c}
    own = (accessory.get("collection") or "").strip()
    if own:
        colls.add(own)
    return colls


def _accessory_profile_tier(accessory: dict, profile: str) -> int:
    """Profile relevance of an accessory: must(0) > should(1) > nice(2) > untagged(3)."""
    if profile in (accessory.get("must_have_profiles") or []):
        return 0
    if profile in (accessory.get("should_have_profiles") or []):
        return 1
    if profile in (accessory.get("nice_to_have_profiles") or []):
        return 2
    return 3


def _rank_by_color(items: list[dict], stroller_colors: set[str], rng: random.Random) -> list[dict]:
    """Colour matches to the stroller first, shuffled within each group, deduped by name."""
    matches = [a for a in items if stroller_colors and (_extract_colors(a.get("name", "")) & stroller_colors)]
    match_ids = {id(a) for a in matches}
    rest = [a for a in items if id(a) not in match_ids]
    rng.shuffle(matches)
    rng.shuffle(rest)

    seen: set[str] = set()
    deduped: list[dict] = []
    for acc in matches + rest:
        norm = re.sub(r"[^a-z0-9]+", "", (acc.get("name") or "").lower())
        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(acc)
    return deduped


def _allocate_by_quota(buckets: dict[str, list[dict]], quota: dict[str, int]) -> list[dict]:
    """Take up to each category's quota, then top up to the cap from leftover items.

    Redistribution prefers must, then should, then nice, so a short category is covered
    by the next-best one rather than left unfilled.
    """
    cap = sum(quota.values())
    order = [c for c in ("must", "should", "nice") if quota.get(c, 0) > 0]
    taken = dict.fromkeys(order, 0)
    selected: list[dict] = []

    for cat in order:
        items = buckets.get(cat, [])
        n = min(quota[cat], len(items))
        selected.extend(items[:n])
        taken[cat] = n

    while len(selected) < cap:
        advanced = False
        for cat in order:
            if len(selected) >= cap:
                break
            items = buckets.get(cat, [])
            if taken[cat] < len(items):
                selected.append(items[taken[cat]])
                taken[cat] += 1
                advanced = True
        if not advanced:
            break
    return selected


def get_cross_sell_items(
    stroller: dict,
    profile: str,
    catalog: CatalogService,
) -> list[dict]:
    """Accessories compatible with the stroller's collection, composed by profile.

    Eligibility is strictly collection-scoped: an accessory matches when the
    stroller's collection appears in its `compatible_collections` (or equals its own
    collection). Strollers whose collection has no compatible accessory show none.

    From that pool, accessories are drawn per the profile's category quota
    (`_CROSS_SELL_QUOTA`) using their must/should/nice tags — untagged accessories are
    never shown. Within a category, colour matches to the stroller rank first.
    """
    collection = (stroller.get("collection") or "").strip()
    if not collection:
        return []

    pool = [a for a in catalog.get_all_accessories() if collection in _accessory_collections(a)]
    if not pool:
        return []

    quota = _CROSS_SELL_QUOTA.get(profile, _CROSS_SELL_QUOTA["B"])
    stroller_colors = _extract_colors(stroller.get("name", ""))
    rng = random.Random()

    buckets: dict[str, list[dict]] = {}
    for acc in pool:
        cat = _TIER_CATEGORY.get(_accessory_profile_tier(acc, profile))
        if cat is None or cat not in quota:
            continue
        buckets.setdefault(cat, []).append(acc)
    for cat in buckets:
        buckets[cat] = _rank_by_color(buckets[cat], stroller_colors, rng)

    return _allocate_by_quota(buckets, quota)


def _extract_colors(name: str) -> set[str]:
    lowered = (name or "").lower()
    colors: set[str] = set()
    for token, canonical in _COLOR_ALIASES.items():
        if token in lowered:
            colors.add(canonical)
    return colors
