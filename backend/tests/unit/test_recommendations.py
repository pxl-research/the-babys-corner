import pytest
from unittest.mock import AsyncMock, patch
from app.services.recommendations import (
    compute_first_nine,
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


def test_first_nine_fills_with_unavailable_if_less_than_three_available():
    strollers = [
        make_stroller("AV1", "A", available=True),
        make_stroller("AV2", "A", available=False),
        make_stroller("AV3", "A", available=False),
    ]
    catalog = make_catalog(strollers)
    order = compute_first_nine("A", catalog)
    assert len(order) == 3


def test_first_nine_skips_llm_when_note_absent():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(5)]
    catalog = make_catalog(strollers)
    # Should work synchronously without LLM
    order = compute_first_nine("A", catalog, optional_note="")
    assert isinstance(order, list)


def test_first_nine_rejects_unknown_llm_ids():
    strollers = [make_stroller(f"ST{i:03}", "A") for i in range(5)]
    catalog = make_catalog(strollers)
    valid_ids = [s["id"] for s in strollers[:5]]
    # Inject a bad LLM response (contains unknown ID)
    bad_llm_order = valid_ids[:4] + ["UNKNOWN_ID"]
    from app.services.recommendations import _validate_llm_order
    result = _validate_llm_order(bad_llm_order, valid_ids)
    assert result is None


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


def test_cross_sell_visibility_by_profile():
    accessories = [
        {
            "id": "ACC001",
            "name": "Regenhoes",
            "brand": "Brand",
            "price": 49.0,
            "description": "desc",
            "image_url": "https://example.com/a.jpg",
            "availability": "Op voorraad",
        }
    ]
    stroller = {**make_stroller("ST001", "A"), "cross_sell_items": ["ACC001"]}
    catalog = CatalogService(strollers=[stroller], accessories=accessories)
    items_a = get_cross_sell_items(stroller, "A", catalog)
    items_b = get_cross_sell_items(stroller, "B", catalog)
    items_c = get_cross_sell_items(stroller, "C", catalog)
    # All profiles get cross-sell items (A hides chips in card but still returns them for modal)
    assert isinstance(items_a, list)
    assert isinstance(items_b, list)
    assert isinstance(items_c, list)


def test_cross_sell_minimalist_quota_and_tiers():
    stroller = {**make_stroller("ST001", "A"), "brand": "bugaboo"}
    accessories = [
        make_accessory(f"AM{i}", f"Must {i}", "bugaboo", must=["A"]) for i in range(5)
    ] + [
        make_accessory(f"AS{i}", f"Should {i}", "bugaboo", should=["A"]) for i in range(3)
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "A", catalog)
    assert len(items) == 5
    must_count = sum(1 for a in items if "A" in a.get("must_have_profiles", []))
    should_count = sum(1 for a in items if "A" in a.get("should_have_profiles", []))
    assert must_count == 4
    assert should_count == 1


def test_cross_sell_ontdekker_quota_and_tiers():
    stroller = {**make_stroller("ST001", "B"), "brand": "joolz"}
    accessories = (
        [make_accessory(f"BM{i}", f"Must {i}", "joolz", must=["B"]) for i in range(8)]
        + [make_accessory(f"BS{i}", f"Should {i}", "joolz", should=["B"]) for i in range(6)]
        + [make_accessory(f"BN{i}", f"Nice {i}", "joolz", nice=["B"]) for i in range(3)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "B", catalog)
    assert len(items) == 10
    assert sum(1 for a in items if "B" in a.get("must_have_profiles", [])) == 6
    assert sum(1 for a in items if "B" in a.get("should_have_profiles", [])) == 3
    assert sum(1 for a in items if "B" in a.get("nice_to_have_profiles", [])) == 1


def test_cross_sell_planner_quota_and_tiers():
    stroller = {**make_stroller("ST001", "C"), "brand": "cybex"}
    accessories = (
        [make_accessory(f"CM{i}", f"Must {i}", "cybex", must=["C"]) for i in range(10)]
        + [make_accessory(f"CS{i}", f"Should {i}", "cybex", should=["C"]) for i in range(8)]
        + [make_accessory(f"CN{i}", f"Nice {i}", "cybex", nice=["C"]) for i in range(3)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "C", catalog)
    assert len(items) == 15
    assert sum(1 for a in items if "C" in a.get("must_have_profiles", [])) == 8
    assert sum(1 for a in items if "C" in a.get("should_have_profiles", [])) == 6
    assert sum(1 for a in items if "C" in a.get("nice_to_have_profiles", [])) == 1


def test_cross_sell_prefers_same_brand_then_falls_back():
    stroller = {**make_stroller("ST001", "B"), "brand": "bugaboo"}
    accessories = (
        [make_accessory(f"M{i}", f"Must {i}", "bugaboo", must=["B"]) for i in range(4)]
        + [make_accessory(f"S{i}", f"Should {i}", "bugaboo", should=["B"]) for i in range(2)]
        + [make_accessory(f"N{i}", f"Nice {i}", "bugaboo", nice=["B"]) for i in range(1)]
        + [make_accessory(f"XM{i}", f"Other Must {i}", "joolz", must=["B"]) for i in range(6)]
        + [make_accessory(f"XS{i}", f"Other Should {i}", "joolz", should=["B"]) for i in range(4)]
        + [make_accessory(f"XN{i}", f"Other Nice {i}", "joolz", nice=["B"]) for i in range(2)]
    )
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "B", catalog)
    assert len(items) == 10
    same_brand = [a for a in items if a["brand"] == "bugaboo"]
    # Uses all available same-brand quota candidates first.
    assert len(same_brand) == 7


def test_cross_sell_dedupes_by_normalized_name():
    stroller = {**make_stroller("ST001", "A"), "brand": "bugaboo"}
    accessories = [
        make_accessory("A1", "Regenhoes Bee", "bugaboo", must=["A"]),
        make_accessory("A2", "regenhoes bee", "bugaboo", must=["A"]),
        make_accessory("A3", "Regenhoes   Bee!!!", "bugaboo", must=["A"]),
        make_accessory("A4", "Must Four", "bugaboo", must=["A"]),
        make_accessory("A5", "Must Five", "bugaboo", must=["A"]),
        make_accessory("A6", "Should One", "bugaboo", should=["A"]),
        make_accessory("A7", "Should Two", "bugaboo", should=["A"]),
        make_accessory("A8", "Should Three", "bugaboo", should=["A"]),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "A", catalog)
    normalized = {
        "".join(ch for ch in a["name"].lower() if ch.isalnum())
        for a in items
    }
    assert len(items) == len(normalized)


def test_cross_sell_keeps_unavailable_items():
    stroller = {**make_stroller("ST001", "A"), "brand": "thule"}
    accessories = [
        make_accessory("A1", "Must 1", "thule", must=["A"], available=False),
        make_accessory("A2", "Must 2", "thule", must=["A"], available=False),
        make_accessory("A3", "Must 3", "thule", must=["A"], available=False),
        make_accessory("A4", "Must 4", "thule", must=["A"], available=False),
        make_accessory("A5", "Should 1", "thule", should=["A"], available=False),
    ]
    catalog = CatalogService(strollers=[stroller], accessories=accessories)

    items = get_cross_sell_items(stroller, "A", catalog)
    assert len(items) == 5
    assert all(not a["availability"] == "Op voorraad" for a in items)
