from app.services.catalog import CatalogService, is_available


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
    cross_ids = stroller.get("cross_sell_items", [])
    items = []
    for id_ in cross_ids:
        acc = catalog.get_accessory(id_)
        if acc and is_available(acc):
            items.append(acc)
    return items
