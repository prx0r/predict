"""bneck calibration — weights emerge from history, not fiat.

Replaces static source weights (arxiv=5, github=4, ...) with learned
P(event | signal, source, topic). Every (source, topic) starts from an
ILLUSTRATIVE prior (n=0, clearly flagged) and moves only on resolved
outcomes. Laplace smoothing throughout.

Store: data/beliefs/calibration.json
"""
from __future__ import annotations

# Illustrative priors from msg-18 discussion. n=0: hypotheses, not facts.
# Single home for venue reliability (peer-review P1#5: killfeed used to
# duplicate these; duplicates rot — import from here).
PRIORS: dict[tuple[str, str], float] = {
    ("polymarket", "high-liquidity"): 0.82,
    ("polymarket", "mid-liquidity"): 0.60,
    ("polymarket", "low-liquidity"): 0.51,
    ("github", "release"): 0.87,
    ("github", "architecture"): 0.61,
    ("arxiv", "benchmark"): 0.75,
    ("x", "calibrated-forecaster"): 0.72,
    ("x", "unrated"): 0.5,
    ("sec-filing", "inventory"): 0.8,
    ("gov-award", "funding"): 0.65,
}


def pm_reliability(venue: str, tier: str) -> float:
    """Prior reliability for a venue book tier (n=0 until resolved outcomes
    move it via record()). Uniform across venues today — exactly what
    killfeed always used (0.82/0.60/0.50); venue differentiation is queued
    pending resolved outcomes, not smuggled in as a silent change."""
    return {"high-liquidity": 0.82, "mid-liquidity": 0.60,
            "low-liquidity": 0.50}.get(tier, 0.50)


def new_table() -> dict:
    return {"entries": {}}


def reliability(table: dict, source: str, topic: str) -> dict:
    e = table.get("entries", {}).get(f"{source}|{topic}")
    if e is None:
        return {"p": PRIORS.get((source, topic), 0.5), "n": 0, "prior": True}
    n, hits = e["n"], e["hits"]
    return {"p": round((hits + 1) / (n + 2), 3), "n": n, "prior": False}


def record(table: dict, source: str, topic: str, correct: bool) -> dict:
    key = f"{source}|{topic}"
    e = table.setdefault("entries", {}).setdefault(key, {"n": 0, "hits": 0})
    e["n"] += 1
    e["hits"] += 1 if correct else 0
    return table
