from app.services.recommendations import (
    compute_first_nine,
    compute_filtered_order,
    compute_progressive_tag_order,
    diversify_llm_order,
    get_batch,
    get_cross_sell_items,
)
from app.services.catalog import CatalogService


def make_stroller(id_, profile_must, profile_nice=None, available=True):
    return {
        "id": id_,
        "name": f"Stroller {id_}",
        "brand": "Brand",
        "price": 100.0,
        "description": "desc",
        "image_url": "https://example.com/img.jpg",
        "availability": "Op voorraad" if available else "Op bestelling",
        "must_have_profiles": [profile_must] if profile_must else [],
        "nice_to_have_profiles": [profile_nice] if profile_nice else [],
        "cross_sell_items": [],
    }


def make_catalog(strollers):
    return CatalogService(strollers=strollers, accessories=[])


def make_accessory(
    id_: str,
    name: str,
    brand: str,
    must: list[str] | None = None,
    should: list[str] | None = None,
    nice: list[str] | None = None,
    available: bool = True,
    collection: str | None = None,
    compatible_collections: list[str] | None = None,
):
    return {
        "id": id_,
        "name": name,
        "brand": brand,
        "price": 25.0,
        "description": "desc",
        "image_url": "https://example.com/acc.jpg",
        "availability": "Op voorraad" if available else "Op bestelling",
        "must_have_profiles": must or [],
        "should_have_profiles": should or [],
        "nice_to_have_profiles": nice or [],
        "collection": collection,
        "compatible_collections": compatible_collections or [],
    }


def test_first_nine_prioritizes_must_then_nice_then_others():
    strollers = [
        make_stroller("OTHER", None),
        make_stroller("NICE", None, "A"),
        make_stroller("MUST", "A"),
    ]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    ids = [s["id"] for s in order]
    assert ids.index("MUST") < ids.index("NICE") < ids.index("OTHER")


def test_first_nine_sorts_available_first_within_tier():
    strollers = [
        make_stroller("UNAVAIL", "A", available=False),
        make_stroller("AVAIL", "A", available=True),
    ]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    ids = [s["id"] for s in order]
    assert ids.index("AVAIL") < ids.index("UNAVAIL")


def test_first_nine_returns_up_to_nine():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(15)]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    assert len(order) == 9


def test_first_nine_randomizes_within_equal_rank_group(monkeypatch):
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(6)]
    catalog = make_catalog(strollers)

    def reverse_shuffle(seq):
        seq.reverse()

    monkeypatch.setattr("app.services.recommendations.random.shuffle", reverse_shuffle)
    order = compute_first_nine("A", catalog)
    ids = [s["id"] for s in order]
    assert ids[0] == "ST005"
    assert ids[-1] == "ST000"


def test_compute_filtered_order_randomizes_equal_groups(monkeypatch):
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(6)]
    catalog = make_catalog(strollers)

    def reverse_shuffle(seq):
        seq.reverse()

    monkeypatch.setattr("app.services.recommendations.random.shuffle", reverse_shuffle)
    order = compute_filtered_order(catalog, "A")
    assert order[0] == "ST005"
    assert order[-1] == "ST000"


def test_first_nine_fills_with_unavailable_if_less_than_three_available():
    strollers = [
        make_stroller("AV1", "A", available=True),
        make_stroller("AV2", "A", available=False),
        make_stroller("AV3", "A", available=False),
    ]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    assert len(order) == 3


def test_first_nine_runs_without_llm():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(5)]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    assert isinstance(order, list)


def test_batch_rotation_returns_existing_batch_idempotently():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(12)]
    catalog = make_catalog(strollers)
    reco_order = [s["id"] for s in compute_first_nine("A", catalog)]
    batch1_a = get_batch(1, reco_order, [], catalog)
    batch1_b = get_batch(1, reco_order, [], catalog)
    assert [p["id"] for p in batch1_a] == [p["id"] for p in batch1_b]


def test_batch_rotation_no_duplicates_until_pool_exhausted():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(9)]
    catalog = make_catalog(strollers)
    reco_order = [s["id"] for s in compute_first_nine("A", catalog)]
    seen = set()
    for i in range(1, 4):
        batch = get_batch(i, reco_order, [], catalog)
        ids = [p["id"] for p in batch]
        assert not seen & set(ids)
        seen |= set(ids)


def test_later_batch_similarity_uses_stroller_favorites_only():
    # Accessory favorites must not influence stroller ranking
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(12)]
    catalog = make_catalog(strollers)
    reco_order = [s["id"] for s in compute_first_nine("A", catalog)]
    # batch 4 should only use stroller favorites for similarity, not accessories
    # (this is a structural assertion — accessory IDs not in stroller pool)
    acc_favs = ["ACC001", "ACC002"]
    batch4 = get_batch(4, reco_order, acc_favs, catalog, stroller_favorites=["ST000"])
    assert all(p["id"].startswith("ST") for p in batch4)


def test_diversify_llm_order_keeps_top_winner_and_randomizes_blocks(monkeypatch):
    strollers = [
        make_stroller("ST_TOP", "A"),       # tier 0
        make_stroller("ST_A1", "A"),        # tier 0
        make_stroller("ST_A2", "A"),        # tier 0
        make_stroller("ST_B1", None, "A"),  # tier 2
        make_stroller("ST_B2", None, "A"),  # tier 2
    ]
    catalog = make_catalog(strollers)
    ordered = ["ST_TOP", "ST_A1", "ST_A2", "ST_B1", "ST_B2"]

    def reverse_shuffle(seq):
        seq.reverse()

    monkeypatch.setattr("app.services.recommendations.random.shuffle", reverse_shuffle)
    diversified = diversify_llm_order(ordered, "A", catalog, keep_top_n=1)
    assert diversified[0] == "ST_TOP"
    # First tail block (same key) reversed.
    assert diversified[1:3] == ["ST_A2", "ST_A1"]


def test_diversify_llm_order_randomizes_non_contiguous_equal_rank(monkeypatch):
    strollers = [
        make_stroller("TOP", "A"),          # keep_top_n
        make_stroller("M1", "A"),
        make_stroller("N1", None, "A"),
        make_stroller("M2", "A"),
        make_stroller("N2", None, "A"),
    ]
    catalog = make_catalog(strollers)
    ordered = ["TOP", "M1", "N1", "M2", "N2"]

    def reverse_shuffle(seq):
        seq.reverse()

    monkeypatch.setattr("app.services.recommendations.random.shuffle", reverse_shuffle)
    diversified = diversify_llm_order(ordered, "A", catalog, keep_top_n=1)
    assert diversified[0] == "TOP"
    # M1/M2 are equal-rank and non-contiguous in tail -> swapped.
    assert diversified[1] == "M2"
    assert diversified[3] == "M1"


def _stroller_in(collection: str, profile: str = "A", name: str = "Stroller") -> dict:
    return {**make_stroller("ST001", profile), "collection": collection, "name": name}


def test_cross_sell_only_returns_collection_compatible():
    stroller = _stroller_in("Fox 5")
    accessories = [
        make_accessory("A1", "Adapter", "bugaboo", compatible_collections=["Fox 5"]),
        make_accessory("A2", "Voetenzak", "bugaboo", collection="Fox 5"),
        make_accessory("X1", "Other adapter", "joolz", compatible_collections=["Donkey"]),
        make_accessory("X2", "Unrelated", "cybex"),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    ids = {a["id"] for a in items}
    assert ids == {"A1", "A2"}


def test_cross_sell_empty_when_no_compatible_accessory():
    stroller = _stroller_in("Coya")
    accessories = [make_accessory("X1", "Adapter", "joolz", compatible_collections=["Donkey"])]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    assert get_cross_sell_items(stroller, "B", catalog) == []


def test_cross_sell_empty_when_stroller_has_no_collection():
    stroller = {**make_stroller("ST001", "A"), "collection": None}
    accessories = [make_accessory("A1", "Adapter", "bugaboo", compatible_collections=["Fox 5"])]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    assert get_cross_sell_items(stroller, "A", catalog) == []


def test_cross_sell_count_scales_by_profile():
    stroller_a = _stroller_in("Fox 5", "A")
    stroller_c = _stroller_in("Fox 5", "C")
    accessories = [
        make_accessory(f"A{i}", f"Item {i}", "bugaboo", compatible_collections=["Fox 5"])
        for i in range(30)
    ]
    catalog = CatalogService(strollers=[stroller_a], accessories=accessories)
    assert len(get_cross_sell_items(stroller_a, "A", catalog)) == 5
    assert len(get_cross_sell_items(stroller_c, "C", catalog)) == 15


def test_cross_sell_dedupes_by_normalized_name():
    stroller = _stroller_in("Fox 5")
    accessories = [
        make_accessory("A1", "Regenhoes Bee", "bugaboo", compatible_collections=["Fox 5"]),
        make_accessory("A2", "regenhoes bee", "bugaboo", compatible_collections=["Fox 5"]),
        make_accessory("A3", "Regenhoes   Bee!!!", "bugaboo", compatible_collections=["Fox 5"]),
        make_accessory("A4", "Voetenzak", "bugaboo", compatible_collections=["Fox 5"]),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    normalized = {"".join(ch for ch in a["name"].lower() if ch.isalnum()) for a in items}
    assert len(items) == len(normalized)


def test_cross_sell_keeps_unavailable_items():
    stroller = _stroller_in("Fox 5")
    accessories = [
        make_accessory(f"A{i}", f"Item {i}", "bugaboo", compatible_collections=["Fox 5"], available=False)
        for i in range(3)
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    assert len(items) == 3
    assert all(a["availability"] != "Op voorraad" for a in items)


def test_cross_sell_prefers_matching_color_in_titles():
    stroller = _stroller_in("Aer²", name="Buggy ultracompact Aer2 - calming beige")
    accessories = [
        make_accessory("M1", "Voetenzak space black", "joolz", compatible_collections=["Aer²"]),
        make_accessory("M2", "Voetenzak calming beige", "joolz", compatible_collections=["Aer²"]),
        make_accessory("M3", "Regenhoes zwart", "joolz", compatible_collections=["Aer²"]),
        make_accessory("M4", "Liner calming beige", "joolz", compatible_collections=["Aer²"]),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    # Capped at 5 for profile A; with beige stroller, beige accessories rank first.
    assert any("beige" in a["name"].lower() for a in items[:2])


# ── progressive tag-drop fallback ────────────────────────────────────────────


def _tagged(id_, tags):
    return {**make_stroller(id_, "A"), "tags": tags}


def test_progressive_tag_order_keeps_all_when_match_exists():
    cat = make_catalog([_tagged("s1", ["X", "Y"]), _tagged("s2", ["X"])])
    order, kept, dropped = compute_progressive_tag_order(cat, "A", ["X", "Y"])
    assert dropped == []
    assert kept == ["X", "Y"]
    assert order == ["s1"]


def test_progressive_tag_order_drops_minimum_tags():
    # No stroller has X+Y+Z. Dropping X leaves {Y,Z} → s3 matches; dropping Y leaves
    # {X,Z} → none. Greedy keeps the most matches, dropping exactly one tag.
    cat = make_catalog([
        _tagged("s1", ["X", "Y"]),
        _tagged("s2", ["X"]),
        _tagged("s3", ["Y", "Z"]),
    ])
    order, kept, dropped = compute_progressive_tag_order(cat, "A", ["X", "Y", "Z"])
    assert dropped == ["X"]
    assert set(kept) == {"Y", "Z"}
    assert order == ["s3"]


def test_progressive_tag_order_all_dropped_falls_back_to_full_set():
    cat = make_catalog([_tagged("s1", ["X"]), _tagged("s2", ["X"])])
    order, kept, dropped = compute_progressive_tag_order(cat, "A", ["NOPE"])
    assert kept == []
    assert dropped == ["NOPE"]
    assert set(order) == {"s1", "s2"}


def test_progressive_tag_order_protects_priority_tag_over_higher_recovery():
    # No stroller has both "0m+" and "X". Dropping "0m+" would recover the most matches
    # (s2, s3), but "0m+" is a priority tag — so "X" is dropped instead and "0m+" survives.
    cat = make_catalog([
        _tagged("s1", ["X"]),
        _tagged("s2", ["0m+"]),
        _tagged("s3", ["0m+"]),
    ])
    order, kept, dropped = compute_progressive_tag_order(cat, "A", ["0m+", "X"])
    assert dropped == ["X"]
    assert kept == ["0m+"]
    assert set(order) == {"s2", "s3"}


def test_progressive_tag_order_drops_priority_only_when_nothing_else_left():
    # "0m+" matches nothing; once the non-priority tag "X" is dropped, the only remaining
    # tag is the priority one, which must then be dropped too.
    cat = make_catalog([_tagged("s1", ["X"]), _tagged("s2", ["Y"])])
    order, kept, dropped = compute_progressive_tag_order(cat, "A", ["0m+", "X"])
    assert dropped == ["X", "0m+"]
    assert kept == []
    assert set(order) == {"s1", "s2"}


def test_progressive_tag_order_keeps_both_priority_tags_longest():
    # Two priority tags + one normal tag, no full match. The normal tag goes first.
    cat = make_catalog([
        _tagged("s1", ["0m+", "Twee kinderen (Duo / Tweeling)"]),
        _tagged("s2", ["Compact"]),
    ])
    order, kept, dropped = compute_progressive_tag_order(
        cat, "A", ["0m+", "Twee kinderen (Duo / Tweeling)", "Compact"]
    )
    assert dropped == ["Compact"]
    assert set(kept) == {"0m+", "Twee kinderen (Duo / Tweeling)"}
    assert order == ["s1"]
