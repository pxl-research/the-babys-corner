from app.services.catalog import CatalogService, is_available
import random
import re

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


def compute_first_nine(
    profile: str,
    catalog: CatalogService,
    optional_note: str = "",
    llm_order: list[str] | None = None,
) -> list[dict]:
    strollers = catalog.get_all_strollers()
    strollers_sorted = sorted(
        strollers,
        key=lambda s: (_tier(s, profile), 0 if is_available(s) else 1),
    )
    first_nine = strollers_sorted[:9]

    if optional_note and llm_order:
        validated = _validate_llm_order(llm_order, [s["id"] for s in first_nine])
        if validated:
            id_map = {s["id"]: s for s in first_nine}
            return [id_map[id_] for id_ in validated]

    return first_nine


def _validate_llm_order(llm_order: list[str], valid_ids: list[str]) -> list[str] | None:
    valid_set = set(valid_ids)
    if any(id_ not in valid_set for id_ in llm_order):
        return None
    if set(llm_order) != valid_set:
        return None
    return llm_order


def compute_filtered_order(
    catalog: CatalogService,
    tags: list[str] | None = None,
    brands: list[str] | None = None,
    collections: list[dict] | None = None,
) -> list[str]:
    """Return all filtered stroller IDs sorted by availability then name (no profile)."""
    strollers = catalog.get_filtered_strollers(tags, brands, collections)
    strollers_sorted = sorted(
        strollers,
        key=lambda s: (0 if is_available(s) else 1, s["name"].lower()),
    )
    return [s["id"] for s in strollers_sorted]


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


def get_cross_sell_items(
    stroller: dict,
    profile: str,
    catalog: CatalogService,
) -> list[dict]:
    quotas = {
        "A": {"must_have_profiles": 4, "should_have_profiles": 1},
        "B": {"must_have_profiles": 6, "should_have_profiles": 3, "nice_to_have_profiles": 1},
        "C": {"must_have_profiles": 8, "should_have_profiles": 6, "nice_to_have_profiles": 1},
    }
    profile_quota = quotas.get(profile, quotas["B"])
    target_total = sum(profile_quota.values())

    rng = random.Random()
    stroller_brand = (stroller.get("brand") or "").strip().lower()
    all_accessories = catalog.get_all_accessories()

    selected: list[dict] = []
    selected_ids: set[str] = set()
    selected_names: set[str] = set()
    stroller_colors = _extract_colors(stroller.get("name", ""))

    def normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (name or "").lower())

    def pick_from_pool(pool: list[dict], count: int) -> list[dict]:
        available = [
            a for a in pool
            if a.get("id") not in selected_ids and normalize_name(a.get("name", "")) not in selected_names
        ]
        if not available or count <= 0:
            return []
        rng.shuffle(available)
        picked: list[dict] = []
        picked_names: set[str] = set()
        for acc in available:
            norm = normalize_name(acc.get("name", ""))
            if norm in picked_names:
                continue
            picked.append(acc)
            picked_names.add(norm)
            if len(picked) == count:
                break
        return picked

    def pick_with_color_priority(pool: list[dict], count: int) -> list[dict]:
        if count <= 0:
            return []
        if not stroller_colors:
            return pick_from_pool(pool, count)
        color_matches = [a for a in pool if _extract_colors(a.get("name", "")) & stroller_colors]
        non_matches = [a for a in pool if a not in color_matches]
        first = pick_from_pool(color_matches, count)
        if len(first) >= count:
            return first
        return first + pick_from_pool(non_matches, count - len(first))

    for tier_field, count in profile_quota.items():
        tier_pool = [a for a in all_accessories if profile in a.get(tier_field, [])]
        same_brand = [a for a in tier_pool if (a.get("brand") or "").strip().lower() == stroller_brand]
        other_brand = [a for a in tier_pool if (a.get("brand") or "").strip().lower() != stroller_brand]

        picked_same = pick_with_color_priority(same_brand, count)
        for acc in picked_same:
            selected.append(acc)
            selected_ids.add(acc["id"])
            selected_names.add(normalize_name(acc.get("name", "")))

        remaining = count - len(picked_same)
        if remaining > 0:
            picked_other = pick_with_color_priority(other_brand, remaining)
            for acc in picked_other:
                selected.append(acc)
                selected_ids.add(acc["id"])
                selected_names.add(normalize_name(acc.get("name", "")))

    if len(selected) < target_total:
        tier_fields = list(profile_quota.keys())
        remainder_pool = [a for a in all_accessories if any(profile in a.get(t, []) for t in tier_fields)]
        same_brand = [a for a in remainder_pool if (a.get("brand") or "").strip().lower() == stroller_brand]
        other_brand = [a for a in remainder_pool if (a.get("brand") or "").strip().lower() != stroller_brand]

        for pool in (same_brand, other_brand):
            needed = target_total - len(selected)
            if needed <= 0:
                break
            extra = pick_with_color_priority(pool, needed)
            for acc in extra:
                selected.append(acc)
                selected_ids.add(acc["id"])
                selected_names.add(normalize_name(acc.get("name", "")))

    rng.shuffle(selected)
    return selected


def _extract_colors(name: str) -> set[str]:
    lowered = (name or "").lower()
    colors: set[str] = set()
    for token, canonical in _COLOR_ALIASES.items():
        if token in lowered:
            colors.add(canonical)
    return colors
