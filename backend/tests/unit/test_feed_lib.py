"""Regression guard for the incremental-feed-update system.

These lock down the one rule that keeps a feed refresh cheap: only NEW strollers and
strollers whose description REALLY changed are handed to the (expensive) LLM passes;
cosmetic description edits and accessory changes never trigger LLM work.
"""

from catalog.feed_lib import diff_feeds, norm_desc, is_stroller_row

STROLLER_CAT = "op stap / kinderwagens en buggy's / complete sets"
ACC_CAT = "op stap / kinderwagens en buggy's / accessoires"


def _row(id_, desc="d", cat=STROLLER_CAT, **extra):
    base = {"id": id_, "description": desc, "Categorie": cat, "title": f"T{id_}", "price": "1.0 EUR"}
    base.update(extra)
    return base


def test_norm_desc_collapses_whitespace_and_strips():
    assert norm_desc("a\n  b &nbsp;") == norm_desc("a b &nbsp;")
    assert norm_desc("  hello   world  ") == "hello world"


def test_is_stroller_row():
    assert is_stroller_row(_row("1")) is True
    assert is_stroller_row(_row("2", cat=ACC_CAT)) is False


def test_added_and_removed_ids():
    old = [_row("1"), _row("2")]
    new = [_row("2"), _row("3")]
    d = diff_feeds(old, new)
    assert d.added_ids == ["3"]
    assert d.removed_ids == ["1"]
    assert d.common_count == 1


def test_cosmetic_description_change_does_not_need_llm():
    old = [_row("1", desc="Line one.\nLine two.")]
    new = [_row("1", desc="Line one. Line two.")]  # only whitespace differs
    d = diff_feeds(old, new)
    assert d.desc_trivial_changed == 1
    assert d.desc_real_changed == []
    assert d.strollers_needing_llm == []


def test_real_description_change_on_stroller_needs_llm():
    old = [_row("1", desc="Old text.")]
    new = [_row("1", desc="Completely new text.")]
    d = diff_feeds(old, new)
    assert d.desc_real_changed == ["1"]
    assert d.strollers_needing_llm == ["1"]


def test_real_description_change_on_accessory_does_not_need_llm():
    old = [_row("1", desc="Old.", cat=ACC_CAT)]
    new = [_row("1", desc="New different.", cat=ACC_CAT)]
    d = diff_feeds(old, new)
    assert d.desc_real_changed == ["1"]          # still reported as a real change
    assert d.strollers_needing_llm == []          # but no LLM work (accessory)


def test_new_stroller_needs_llm_new_accessory_does_not():
    old = [_row("1")]
    new = [_row("1"), _row("2"), _row("3", cat=ACC_CAT)]
    d = diff_feeds(old, new)
    assert d.new_strollers == ["2"]
    assert d.strollers_needing_llm == ["2"]


def test_field_changes_counted():
    old = [_row("1", price="1.0 EUR"), _row("2", title="A")]
    new = [_row("1", price="2.0 EUR"), _row("2", title="B")]
    d = diff_feeds(old, new)
    assert d.field_changes.get("price") == 1
    assert d.field_changes.get("title") == 1


def test_column_diff():
    d = diff_feeds([_row("1")], [_row("1")], old_columns=["id", "x"], new_columns=["id", "y"])
    assert d.added_columns == ["y"]
    assert d.removed_columns == ["x"]
