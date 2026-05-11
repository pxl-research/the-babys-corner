import pytest
from app.services.catalog import CatalogService, is_available

VALID_STROLLER = {
    "id": "ST_TEST",
    "name": "Test Stroller",
    "brand": "TestBrand",
    "price": 999.0,
    "description": "Test desc",
    "image_url": "https://example.com/img.jpg",
    "availability": "Op voorraad",
    "must_have_profiles": ["A"],
    "nice_to_have_profiles": [],
    "cross_sell_items": [],
}


def test_catalog_loads_strollers_from_dummy():
    catalog = CatalogService()
    strollers = catalog.get_all_strollers()
    assert len(strollers) > 0
    assert all("id" in s for s in strollers)


def test_catalog_loads_accessories_from_dummy():
    catalog = CatalogService()
    accessories = catalog.get_all_accessories()
    assert len(accessories) > 0


def test_catalog_skips_items_missing_required_fields():
    bad_item = {"id": "ST_BAD"}
    good_item = {**VALID_STROLLER, "id": "ST_GOOD"}
    catalog = CatalogService(strollers=[bad_item, good_item], accessories=[])
    strollers = catalog.get_all_strollers()
    assert len(strollers) == 1
    assert strollers[0]["id"] == "ST_GOOD"


def test_get_stroller_by_id():
    catalog = CatalogService(strollers=[VALID_STROLLER], accessories=[])
    assert catalog.get_stroller("ST_TEST") is not None
    assert catalog.get_stroller("MISSING") is None


def test_is_available_only_op_voorraad():
    assert is_available({"availability": "Op voorraad"}) is True
    assert is_available({"availability": "Op bestelling"}) is False
    assert is_available({"availability": "Niet beschikbaar"}) is False
    assert is_available({}) is False
