from app.content import load_categories, category_label, category_labels


def test_load_categories_has_eight_entries():
    config = load_categories()
    assert len(config["categories"]) == 8


def test_category_ids_are_unique():
    config = load_categories()
    ids = [c["id"] for c in config["categories"]]
    assert len(ids) == len(set(ids))


def test_strollers_is_ai_with_intro():
    config = load_categories()
    strollers = next(c for c in config["categories"] if c["id"] == "strollers")
    assert strollers["status"] == "ai"
    assert strollers["intro"] and len(strollers["intro"]) > 0


def test_non_stroller_categories_are_soon():
    config = load_categories()
    for cat in config["categories"]:
        if cat["id"] != "strollers":
            assert cat["status"] == "soon"
            assert cat["intro"] is None


def test_overview_intro_present():
    config = load_categories()
    assert config["overview_intro"] and len(config["overview_intro"]) > 0


def test_category_label_strollers():
    assert category_label("strollers") == "Kinderwagens & buggy's"


def test_category_label_unknown_returns_id():
    assert category_label("unknown_cat") == "unknown_cat"


def test_category_labels_multiple():
    labels = category_labels(["strollers", "car_seats"])
    assert labels[0] == "Kinderwagens & buggy's"
    assert labels[1] == "Autostoelen"
