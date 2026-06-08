from app.services.recommendations import (
    BATCH_SIZE,
    tiered_batch_ids,
    compute_first_nine,
    compute_filtered_order,
    compute_progressive_tag_order,
    compute_tiered_tag_order,
    reorder_within_tiers,
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


def test_batch_one_fills_the_grid():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(20)]
    catalog = make_catalog(strollers)
    reco_order = [s["id"] for s in compute_first_nine("A", catalog)]
    batch1 = get_batch(1, reco_order, [], catalog)
    assert len(batch1) == BATCH_SIZE


def test_batch_rotation_no_duplicates_until_pool_exhausted():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(20)]
    catalog = make_catalog(strollers)
    reco_order = [s["id"] for s in compute_first_nine("A", catalog)]
    seen = set()
    for i in range(1, 4):
        batch = get_batch(i, reco_order, [], catalog)
        ids = [p["id"] for p in batch]
        assert not seen & set(ids)
        seen |= set(ids)
    assert len(seen) == 20


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
        make_accessory("A1", "Adapter", "bugaboo", compatible_collections=["Fox 5"], must=["A"]),
        make_accessory("A2", "Voetenzak", "bugaboo", collection="Fox 5", must=["A"]),
        make_accessory("X1", "Other adapter", "joolz", compatible_collections=["Donkey"], must=["A"]),
        make_accessory("X2", "Unrelated", "cybex", must=["A"]),
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
        make_accessory(f"A{i}", f"Item {i}", "bugaboo", compatible_collections=["Fox 5"], must=["A", "B", "C"])
        for i in range(30)
    ]
    catalog = CatalogService(strollers=[stroller_a], accessories=accessories)
    assert len(get_cross_sell_items(stroller_a, "A", catalog)) == 5
    assert len(get_cross_sell_items(stroller_c, "C", catalog)) == 15


def test_cross_sell_dedupes_by_normalized_name():
    stroller = _stroller_in("Fox 5")
    accessories = [
        make_accessory("A1", "Regenhoes Bee", "bugaboo", compatible_collections=["Fox 5"], must=["A"]),
        make_accessory("A2", "regenhoes bee", "bugaboo", compatible_collections=["Fox 5"], must=["A"]),
        make_accessory("A3", "Regenhoes   Bee!!!", "bugaboo", compatible_collections=["Fox 5"], must=["A"]),
        make_accessory("A4", "Voetenzak", "bugaboo", compatible_collections=["Fox 5"], must=["A"]),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    normalized = {"".join(ch for ch in a["name"].lower() if ch.isalnum()) for a in items}
    assert len(items) == len(normalized)


def test_cross_sell_keeps_unavailable_items():
    stroller = _stroller_in("Fox 5")
    accessories = [
        make_accessory(f"A{i}", f"Item {i}", "bugaboo", compatible_collections=["Fox 5"], available=False, must=["A"])
        for i in range(3)
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    assert len(items) == 3
    assert all(a["availability"] != "Op voorraad" for a in items)


def test_cross_sell_prefers_matching_color_in_titles():
    stroller = _stroller_in("Aer²", name="Buggy ultracompact Aer2 - calming beige")
    accessories = [
        make_accessory("M1", "Voetenzak space black", "joolz", compatible_collections=["Aer²"], must=["A"]),
        make_accessory("M2", "Voetenzak calming beige", "joolz", compatible_collections=["Aer²"], must=["A"]),
        make_accessory("M3", "Regenhoes zwart", "joolz", compatible_collections=["Aer²"], must=["A"]),
        make_accessory("M4", "Liner calming beige", "joolz", compatible_collections=["Aer²"], must=["A"]),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    # Capped at 5 for profile A; with beige stroller, beige accessories rank first.
    assert any("beige" in a["name"].lower() for a in items[:2])


def _acc(id_, must=None, should=None, nice=None):
    return make_accessory(id_, f"Item {id_}", "bugaboo", compatible_collections=["Fox 5"],
                          must=must, should=should, nice=nice)


def test_cross_sell_minimalist_is_must_only():
    # Profile A draws ONLY from must — should/nice/untagged are excluded entirely.
    stroller = _stroller_in("Fox 5")
    accessories = (
        [_acc(f"M{i}", must=["A"]) for i in range(3)]
        + [_acc(f"S{i}", should=["A"]) for i in range(3)]
        + [_acc(f"N{i}", nice=["A"]) for i in range(3)]
        + [_acc(f"O{i}") for i in range(3)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    ids = {a["id"] for a in get_cross_sell_items(stroller, "A", catalog)}
    assert ids == {"M0", "M1", "M2"}


def test_cross_sell_minimalist_shows_fewer_when_must_short():
    # Fewer than 5 must → show only those, never backfill from should/nice.
    stroller = _stroller_in("Fox 5")
    accessories = [_acc("M0", must=["A"]), _acc("M1", must=["A"])] + [_acc(f"S{i}", should=["A"]) for i in range(10)]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "A", catalog)
    assert {a["id"] for a in items} == {"M0", "M1"}


def test_cross_sell_ontdekker_is_mostly_must_few_should():
    # Profile B (cap 10): 7 must + 3 should when both are plentiful; no nice/untagged.
    stroller = _stroller_in("Fox 5")
    accessories = (
        [_acc(f"M{i}", must=["B"]) for i in range(20)]
        + [_acc(f"S{i}", should=["B"]) for i in range(20)]
        + [_acc(f"N{i}", nice=["B"]) for i in range(20)]
        + [_acc(f"O{i}") for i in range(20)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "B", catalog)
    assert len(items) == 10
    n_must = sum(1 for a in items if a["id"].startswith("M"))
    n_should = sum(1 for a in items if a["id"].startswith("S"))
    assert (n_must, n_should) == (7, 3)


def test_cross_sell_ontdekker_rebalances_when_must_short():
    # B with only 4 must → fill the rest of the cap with should (still no nice/untagged).
    stroller = _stroller_in("Fox 5")
    accessories = (
        [_acc(f"M{i}", must=["B"]) for i in range(4)]
        + [_acc(f"S{i}", should=["B"]) for i in range(20)]
        + [_acc(f"N{i}", nice=["B"]) for i in range(20)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "B", catalog)
    ids = [a["id"] for a in items]
    assert len(ids) == 10
    assert sum(1 for x in ids if x.startswith("M")) == 4
    assert sum(1 for x in ids if x.startswith("S")) == 6
    assert not any(x.startswith("N") for x in ids)


def test_cross_sell_planner_is_even_split():
    # Profile C (cap 15): even 5/5/5 across must/should/nice; no untagged.
    stroller = _stroller_in("Fox 5")
    accessories = (
        [_acc(f"M{i}", must=["C"]) for i in range(20)]
        + [_acc(f"S{i}", should=["C"]) for i in range(20)]
        + [_acc(f"N{i}", nice=["C"]) for i in range(20)]
        + [_acc(f"O{i}") for i in range(20)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "C", catalog)
    ids = [a["id"] for a in items]
    assert len(ids) == 15
    counts = (
        sum(1 for x in ids if x.startswith("M")),
        sum(1 for x in ids if x.startswith("S")),
        sum(1 for x in ids if x.startswith("N")),
    )
    assert counts == (5, 5, 5)
    assert not any(x.startswith("O") for x in ids)


def test_cross_sell_planner_rebalances_when_category_short():
    # C with only 3 must → top up the cap from should/nice (must-first), still no untagged.
    stroller = _stroller_in("Fox 5")
    accessories = (
        [_acc(f"M{i}", must=["C"]) for i in range(3)]
        + [_acc(f"S{i}", should=["C"]) for i in range(20)]
        + [_acc(f"N{i}", nice=["C"]) for i in range(20)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items = get_cross_sell_items(stroller, "C", catalog)
    ids = [a["id"] for a in items]
    assert len(ids) == 15
    assert sum(1 for x in ids if x.startswith("M")) == 3


# ── tiered batch row-fill ────────────────────────────────────────────────────


def _tiers(*specs):
    # specs: (start, count) pairs; labels are irrelevant to slicing
    return [{"label": f"t{i}", "start": s, "count": c} for i, (s, c) in enumerate(specs)]


def test_tiered_batch_fills_last_tier_to_full_row():
    # 2 exact + a large relaxed tier. Base batch of 9 would show 7 relaxed (orphan row);
    # row-fill extends to 9 relaxed so the section ends on a full row of 3.
    order = [f"x{i}" for i in range(30)]
    tiers = _tiers((0, 2), (2, 28))
    ids = tiered_batch_ids(order, tiers, already_shown=0, batch_size=9)
    assert len(ids) == 11           # 2 exact + 9 relaxed
    assert ids[:2] == ["x0", "x1"]  # exact tier left at its natural 2 (data-limited)
    assert (len(ids) - 2) % 3 == 0  # relaxed section fills full rows


def test_tiered_batch_is_contiguous_across_batches():
    order = [f"x{i}" for i in range(30)]
    tiers = _tiers((0, 2), (2, 28))
    b1 = tiered_batch_ids(order, tiers, already_shown=0, batch_size=9)
    b2 = tiered_batch_ids(order, tiers, already_shown=len(b1), batch_size=9)
    assert set(b1) & set(b2) == set()          # no overlap
    assert b1 + b2 == order[: len(b1) + len(b2)]  # contiguous
    assert len(b2) % 3 == 0                     # next batch also row-aligned


def test_tiered_batch_short_tier_not_padded_past_its_end():
    # Last tier has only 4 items (total 6); can't reach a multiple of 3, so it's shown
    # whole — the short final row is unavoidable ("no more results in this tier").
    order = [f"x{i}" for i in range(6)]
    tiers = _tiers((0, 2), (2, 4))
    ids = tiered_batch_ids(order, tiers, already_shown=0, batch_size=9)
    assert ids == order  # all 6, capped at the assortment


def test_tiered_batch_empty_when_exhausted():
    order = [f"x{i}" for i in range(6)]
    tiers = _tiers((0, 6))
    assert tiered_batch_ids(order, tiers, already_shown=6, batch_size=9) == []


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


# ── tiered relaxed recommendations ───────────────────────────────────────────


def test_tiered_order_exact_first_then_relaxed_tiers():
    # s1 matches X+Y (exact); s2 matches X only; s3 matches neither tag.
    cat = make_catalog([
        _tagged("s1", ["X", "Y"]),
        _tagged("s2", ["X"]),
        _tagged("s3", ["Z"]),
    ])
    reco, tiers, primary = compute_tiered_tag_order(cat, "A", ["X", "Y"])
    # Tier 0 exact = s1; later tiers unlock s2 then s3, each only the NEW ids.
    assert reco[0] == "s1"
    assert set(reco) == {"s1", "s2", "s3"}
    assert tiers[0]["label"] == "Exacte matches"
    assert tiers[0]["start"] == 0 and tiers[0]["count"] == 1
    # Tiers segment the flat list without overlap, covering every id.
    assert sum(t["count"] for t in tiers) == len(reco)
    assert primary == ["X", "Y"]


def test_tiered_order_best_matches_first_when_no_exact():
    # No stroller has both X and Y → tier 0 (exact) is empty, first shown is "Beste matches".
    cat = make_catalog([_tagged("s1", ["X"]), _tagged("s2", ["Y"])])
    reco, tiers, primary = compute_tiered_tag_order(cat, "A", ["X", "Y"])
    assert tiers[0]["label"] == "Beste matches"
    assert set(reco) == {"s1", "s2"}


def test_tiered_order_protects_priority_tag_to_deepest_tier():
    # s_duo has only the priority tag; s_other has only the normal tag X.
    DUO = "Twee kinderen (Duo / Tweeling)"
    cat = make_catalog([_tagged("s_duo", [DUO]), _tagged("s_other", ["X"])])
    reco, tiers, _ = compute_tiered_tag_order(cat, "A", [DUO, "X"])
    # Relaxing X (non-priority) comes before relaxing the priority duo tag, so the
    # duo stroller is unlocked in an earlier tier than the non-duo one.
    assert reco.index("s_duo") < reco.index("s_other")


def test_reorder_within_tiers_preserves_boundaries():
    reco = ["a", "b", "c", "d"]
    tiers = [
        {"label": "Exacte matches", "start": 0, "count": 2},
        {"label": "Ruimere selectie", "start": 2, "count": 2},
    ]
    # A note rerank floats "d" (tier 1) and "b" (tier 0) to the front globally.
    new_order = ["d", "b", "a", "c"]
    ordered, rebuilt = reorder_within_tiers(reco, tiers, new_order)
    # Each id stays in its tier; within-tier note order is honoured (b before a).
    assert ordered == ["b", "a", "d", "c"]
    assert [t["start"] for t in rebuilt] == [0, 2]
    assert [t["count"] for t in rebuilt] == [2, 2]
