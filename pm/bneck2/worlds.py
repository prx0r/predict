"""bneck2 worlds — Post-AGI World-State -> Obsolescence engine (msg 21).

Alpha != W_future - W_today. Instead:
  Signal_company = SUM_s (P_you,s - P_market,s) x Impact(company,s) x Duration

You don't need to know WHO wins. You need incumbents whose profit pools
cannot survive the range of plausible futures (obsolescence arbitrage):
impaired in ~all you-weighted futures while the market prices survival.

Worlds carry BOTH probabilities (ours + market-implied). Evidence (papers,
benchmarks, milestones) moves p_you; prediction markets discipline p_market.
A capability milestone (J_t jump, e.g. Navier-Stokes-scale result) reprices
worlds first, companies second — years before commercialization.

Seed: data/worlds/worlds.json (2031 agent-regime set from msg 21).
p_market values are PLACEHOLDER assumptions, explicitly marked, to be
replaced by prediction-market/equity-implied calibration. Stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLDS_PATH = ROOT / "data" / "worlds" / "worlds.json"


def load_worlds(path: Path = WORLDS_PATH) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.setdefault("worlds", [])
    doc.setdefault("incumbents", [])
    return doc


def world_gaps(worlds: list[dict]) -> list[dict]:
    """Per-world disagreement: ours minus market."""
    return [{"id": w["id"], "label": w.get("label", w["id"]),
             "p_you": w["p_you"], "p_market": w["p_market"],
             "gap": round(w["p_you"] - w["p_market"], 3)} for w in worlds]


def survival_stats(inc: dict, worlds: list[dict]) -> dict:
    """You-weighted survival vs market-priced survival."""
    surv = inc.get("survives", {})
    you = sum(w["p_you"] * float(surv.get(w["id"], 1.0)) for w in worlds)
    impaired_in = sum(w["p_you"] for w in worlds
                      if float(surv.get(w["id"], 1.0)) < 0.5)
    return {"p_you_survive": round(you, 3),
            "p_market_survive": inc.get("market_survival_p", 1.0),
            "gap": round(inc.get("market_survival_p", 1.0) - you, 3),
            "impaired_share": round(impaired_in, 3)}


def signal_company(inc: dict, worlds: list[dict]) -> dict:
    """SUM_s (P_you - P_market) x Impact x Duration. Negative = the pool
    shrinks in our distribution vs market pricing -> short-side candidate."""
    surv = inc.get("survives", {})
    duration = float(inc.get("tech_duration_years") if inc.get("tech_duration_years") is not None else 5.0)
    pool = float(inc.get("profit_pool_usd") if inc.get("profit_pool_usd") is not None else 0.0)
    total, terms = 0.0, []
    for w in worlds:
        gap = w["p_you"] - w["p_market"]
        impact = -pool * (1.0 - float(surv.get(w["id"], 1.0)))
        terms.append({"world": w["id"], "gap": round(gap, 3),
                      "impact_usd": round(impact)})
        total += gap * impact * duration
    stats = survival_stats(inc, worlds)
    verdict = "NONE"
    if stats["gap"] >= 0.4 and stats["impaired_share"] >= 0.8:
        verdict = "OBSOLESCENCE_ARBITRAGE"
    elif stats["gap"] >= 0.25:
        verdict = "WATCH"
    return {"incumbent": inc["id"], "label": inc.get("label", inc["id"]),
            "signal_usd": round(total), "terms": terms,
            "duration_years": duration, **stats, "verdict": verdict}


def screen(doc: dict | None = None) -> list[dict]:
    doc = doc or load_worlds()
    return sorted((signal_company(i, doc["worlds"]) for i in doc["incumbents"]),
                  key=lambda r: r["signal_usd"])
