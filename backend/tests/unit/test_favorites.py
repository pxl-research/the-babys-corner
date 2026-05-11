import pytest
from app.services.catalog import CatalogService, is_available

UNAVAILABLE_STROLLER = {
    "id": "ST_UNAVAIL",
    "name": "Unavailable",
    "brand": "B",
    "price": 100.0,
    "description": "d",
    "image_url": "https://example.com/img.jpg",
    "availability": "Op bestelling",
    "must_have_profiles": [],
    "nice_to_have_profiles": [],
    "cross_sell_items": [],
}

UNAVAILABLE_ACC = {
    "id": "ACC_UNAVAIL",
    "name": "Unavailable Acc",
    "brand": "B",
    "price": 20.0,
    "description": "d",
    "image_url": "https://example.com/img.jpg",
    "availability": "Op bestelling",
}


def test_unavailable_stroller_favorite_disabled():
    assert not is_available(UNAVAILABLE_STROLLER)


def test_unavailable_already_favorited_accessory_can_be_removed_not_added():
    # Simulate: ACC_UNAVAIL is already in favorites → remove allowed, re-add not
    favorites = ["ACC_UNAVAIL"]
    catalog = CatalogService(strollers=[], accessories=[UNAVAILABLE_ACC])
    acc = catalog.get_accessory("ACC_UNAVAIL")
    assert acc is not None
    # Already favorited + unavailable → can remove (toggle removes it)
    assert "ACC_UNAVAIL" in favorites
    # Remove
    favorites.remove("ACC_UNAVAIL")
    assert "ACC_UNAVAIL" not in favorites
    # Cannot re-add because unavailable
    assert not is_available(acc)


def test_available_stroller_can_be_favorited():
    avail = {**UNAVAILABLE_STROLLER, "id": "ST_OK", "availability": "Op voorraad"}
    assert is_available(avail)
