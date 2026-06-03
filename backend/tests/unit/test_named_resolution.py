from app.services.session_service import (
    resolve_strollers,
    resolve_accessories,
    resolve_stroller_batches,
    session_detail_from_row,
)


class _FakeCatalog:
    def __init__(self):
        self._strollers = {
            "ST001": {"id": "ST001", "name": "Fox 5", "brand": "bugaboo"},
            "ST002": {"id": "ST002", "name": "Cruz", "brand": "uppababy"},
        }
        self._accessories = {
            "AC001": {"id": "AC001", "name": "Voetenzak", "brand": "bugaboo"},
        }

    def get_stroller(self, id_):
        return self._strollers.get(id_)

    def get_accessory(self, id_):
        return self._accessories.get(id_)


def test_resolve_strollers_maps_known_drops_unknown_keeps_order():
    cat = _FakeCatalog()
    out = resolve_strollers(["ST002", "NOPE", "ST001"], cat)
    assert [n.id for n in out] == ["ST002", "ST001"]
    assert out[0].name == "Cruz"
    assert out[0].brand == "uppababy"


def test_resolve_accessories_maps_known_only():
    cat = _FakeCatalog()
    out = resolve_accessories(["AC001", "MISSING"], cat)
    assert [n.id for n in out] == ["AC001"]
    assert out[0].name == "Voetenzak"


def test_resolve_stroller_batches_preserves_batch_shape():
    cat = _FakeCatalog()
    out = resolve_stroller_batches([["ST001"], ["ST002", "NOPE"]], cat)
    assert [[n.id for n in batch] for batch in out] == [["ST001"], ["ST002"]]


def test_session_detail_resolves_names_when_catalog_supplied():
    cat = _FakeCatalog()
    row = {
        "session_id": "S1",
        "session_code": "ABC123",
        "source": "store",
        "status": "handed_off",
        "started_at": "2026-06-03T10:00:00+00:00",
        "handoff_at": None,
        "derived_profile": "B",
        "quiz_answers": "[]",
        "optional_note": None,
        "shown_products": '[["ST001", "ST002"]]',
        "stroller_favorites": '["ST001"]',
        "accessory_favorites": '["AC001"]',
        "llm_talking_points": None,
        "email_status": "not_sent",
    }
    detail = session_detail_from_row(row, cat)
    assert [n.name for n in detail.stroller_favorites_named] == ["Fox 5"]
    assert [n.name for n in detail.accessory_favorites_named] == ["Voetenzak"]
    assert detail.shown_products_named[0][1].name == "Cruz"
    # Raw ID lists remain intact alongside the resolved names.
    assert detail.stroller_favorites == ["ST001"]


def test_session_detail_without_catalog_leaves_named_empty():
    row = {
        "session_id": "S1",
        "session_code": "ABC123",
        "source": "home",
        "status": "active",
        "started_at": "2026-06-03T10:00:00+00:00",
        "stroller_favorites": '["ST001"]',
    }
    detail = session_detail_from_row(row)
    assert detail.stroller_favorites_named == []
    assert detail.stroller_favorites == ["ST001"]
