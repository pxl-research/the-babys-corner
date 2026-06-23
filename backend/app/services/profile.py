from collections import Counter

# Profile = the most-chosen answer profile. Ties are broken by this priority order:
# B (Ontdekker) stays the safe default, then C (Planner) beats A (Minimalist) — so a
# straight A&C tie resolves to C (Planner), per spec §2 "Bij gelijkstand A & C → profiel C".
# max() returns the first element reaching the highest count, so list order = tie priority.
_TIEBREAK = ["B", "C", "A"]


def compute_profile(answers: list[dict]) -> str:
    counts: Counter = Counter(a["profile"] for a in answers)
    return max(_TIEBREAK, key=lambda p: counts.get(p, 0))
