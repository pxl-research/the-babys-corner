from app.services.profile import compute_profile


def _answers(profile_list: list[str]) -> list[dict]:
    return [{"profile": p} for p in profile_list]


def test_compute_profile_clean_win():
    assert compute_profile(_answers(["A", "A", "A", "B", "C"])) == "A"


def test_compute_profile_tie_b_beats_a():
    assert compute_profile(_answers(["A", "A", "B", "B", "C"])) == "B"


def test_compute_profile_tie_a_beats_c():
    assert compute_profile(_answers(["A", "A", "C", "C", "B"])) == "A"


def test_compute_profile_tie_b_beats_c():
    assert compute_profile(_answers(["B", "B", "C", "C", "A"])) == "B"


def test_compute_profile_three_way_tie_returns_b():
    # 5 answers — impossible true 3-way but test tiebreak chain
    # 2A 2B 1C → B beats A (tie-break B > A)
    assert compute_profile(_answers(["A", "A", "B", "B", "C"])) == "B"
    # 1A 2B 2C → B beats C
    assert compute_profile(_answers(["A", "B", "B", "C", "C"])) == "B"


def test_compute_profile_all_five_answered():
    assert compute_profile(_answers(["C", "C", "C", "C", "C"])) == "C"
