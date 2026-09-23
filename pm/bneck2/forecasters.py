"""bneck forecasters — Skill_i(topic): who knew first, and was right?

Per (handle, topic): calibration (Brier), lead time, specificity, novelty,
independence, revision discipline. Laplace prior (0.5, weight 2) so newcomers
start neutral and evidence moves them. Domain-separated: semiconductors !=
biology != quantum.

weight(handle, topic) is what prices an X post into a claim — followers
never enter the formula.

Stdlib only. Store: data/beliefs/forecasters.json
"""
from __future__ import annotations

PRIOR_P = 0.5
PRIOR_W = 2.0


def new_book() -> dict:
    return {"handles": {}}


def _topic(book: dict, handle: str, topic: str) -> dict:
    return (book.setdefault("handles", {}).setdefault(handle, {})
            .setdefault("topics", {}).setdefault(topic, {
                "n": 0, "brier_sum": 0.0, "lead_days": [],
                "specific": 0, "novel": 0, "independent": 0, "revisions": 0}))


def record(book: dict, handle: str, topic: str, predicted_p: float,
           occurred: bool, lead_days: float = 0.0, specific: bool = True,
           novel: bool = False, independent: bool = True,
           revised_after_wrong: bool = False) -> dict:
    """Log one resolved forecast. occurred = ground truth (1/0)."""
    t = _topic(book, handle, topic)
    t["n"] += 1
    t["brier_sum"] += (float(predicted_p) - (1.0 if occurred else 0.0)) ** 2
    t["lead_days"].append(float(lead_days))
    t["specific"] += 1 if specific else 0
    t["novel"] += 1 if novel else 0
    t["independent"] += 1 if independent else 0
    t["revisions"] += 1 if revised_after_wrong else 0
    return book


def skill(book: dict, handle: str, topic: str) -> dict:
    """Composite 0-1 skill with prior. Transparent components for audit."""
    t = _topic(book, handle, topic)
    n = t["n"]
    brier = t["brier_sum"] / n if n else 0.25
    calibration = max(0.0, 1.0 - 2.0 * brier)  # 1.0 perfect, 0.5 coin-flip, 0 worse
    lead = sum(t["lead_days"]) / len(t["lead_days"]) if t["lead_days"] else 0.0
    lead_score = min(1.0, max(0.0, lead) / 30.0)  # 30+ days early = full marks
    spec = t["specific"] / n if n else 0.5
    nov = t["novel"] / n if n else 0.0
    ind = t["independent"] / n if n else 0.5
    raw = (0.4 * calibration + 0.2 * lead_score + 0.15 * spec
           + 0.15 * nov + 0.1 * ind)
    pooled = (PRIOR_W * PRIOR_P + n * raw) / (PRIOR_W + n)
    return {"skill": round(pooled, 3), "n": n,
            "calibration": round(calibration, 3), "lead_days_avg": round(lead, 1),
            "specificity": round(spec, 3), "novelty": round(nov, 3),
            "independence": round(ind, 3), "revisions": t["revisions"]}


def weight(book: dict, handle: str, topic: str) -> float:
    """Claim weight for this author on this topic. Unknown handle -> prior."""
    return skill(book, handle, topic)["skill"]
