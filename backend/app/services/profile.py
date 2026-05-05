from collections import Counter

_TIEBREAK = ["B", "A", "C"]


def compute_profile(answers: list[dict]) -> str:
    counts: Counter = Counter(a["profile"] for a in answers)
    return max(_TIEBREAK, key=lambda p: counts.get(p, 0))
