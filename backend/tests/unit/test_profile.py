from app.services.profile import compute_profile


def _answers(profile_list: list[str]) -> list[dict]:
    return [{"profile": p} for p in profile_list]


def test_compute_profile_clean_win():
    assert compute_profile(_answers(["A", "A", "A", "B", "C"])) == "A"


def test_compute_profile_tie_b_beats_a():
    assert compute_profile(_answers(["A", "A", "B", "B", "C"])) == "B"


def test_compute_profile_tie_c_beats_a():
    # Spec §2: bij gelijkstand A & C → profiel C (Planner).
    assert compute_profile(_answers(["A", "A", "C", "C", "B"])) == "C"


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


# ── 2-question profile (current flow, spec §2) ───────────────────────────────


def test_compute_profile_two_q_clean_win():
    assert compute_profile(_answers(["A", "A"])) == "A"
    assert compute_profile(_answers(["C", "C"])) == "C"


def test_compute_profile_two_q_tie_a_and_c_returns_c():
    # Spec §2: bij gelijkstand A & C → profiel C (Planner).
    assert compute_profile(_answers(["A", "C"])) == "C"


def test_compute_profile_two_q_tie_with_b_stays_b():
    # B (Ontdekker) keeps priority over A and C on a straight 1-1 tie.
    assert compute_profile(_answers(["A", "B"])) == "B"
    assert compute_profile(_answers(["B", "C"])) == "B"


# ── legacy multi-answer cases (compute_profile is count-agnostic) ─────────────


def test_compute_profile_three_q_two_b_one_a():
    assert compute_profile(_answers(["B", "B", "A"])) == "B"


def test_compute_profile_three_q_perfect_spread_returns_b():
    assert compute_profile(_answers(["A", "B", "C"])) == "B"


def test_compute_profile_three_q_clean_win():
    assert compute_profile(_answers(["A", "A", "B"])) == "A"
    assert compute_profile(_answers(["C", "C", "A"])) == "C"
