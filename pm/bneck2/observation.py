"""OBSERVATION primitive — Apify (or any) records become edge evidence.

Every scraper produces OBSERVATIONs; the mapper routes constraint-relevant
ones into typed edge/node fields. Web gives state, we store motion:
observations accumulate per (subject, predicate) and the DERIVATIVE is the
signal. Stdlib only. No runs executed here — registry is seed-unverified.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# signal family -> (target kind, edge/node field, note)
ROUTES = {
    "lead_time_mention": ("edge.supply", "lead_time_months",
                          "max reported weeks wins until contradicted"),
    "capacity_announcement": ("edge.supply", "global_capacity",
                              "dated, sourced MW/units only"),
    "utilization_mention": ("edge.supply", "utilization",
                            "fraction 0-1 with source"),
    "shortage_complaint": ("edge.supply", "utilization",
                           "complaint velocity proxies tightness"),
    "substitute_mention": ("edge.substitution", "alternatives",
                           "append alternative + source"),
    "tender_award": ("node", "evidence",
                     "PUBLIC_CAPITAL_COMMITMENT: value + buyer + winner"),
    "hiring_surge": ("node", "evidence",
                     "role-taxonomy drift = bottleneck migration signal"),
    "price_increase": ("edge.supply", "evidence",
                       "supplier pricing power = tightness"),
    "new_factory": ("edge.supply", "capacity_growth_rate",
                    "capacity coming + date"),
}


def observe(subject: str, predicate: str, obj: str, time: str,
            source: str, confidence: float = 0.5,
            location: str = "", actor: str = "") -> dict:
    return {"subject": subject, "predicate": predicate, "object": obj,
            "time": time, "location": location, "source": source,
            "confidence": confidence, "observed_at": time,
            "source_actor": actor}


def route(obs: dict) -> dict:
    """Where does this observation go in the graph? (pure, no writes)."""
    pred = obs.get("predicate", "")
    if pred not in ROUTES:
        return {"route": "node.evidence (unmapped family)",
                "reason": f"no route for {pred!r}"}
    kind, field, note = ROUTES[pred]
    return {"route": f"{kind}.{field}", "note": note,
            "subject": obs.get("subject")}


def motion(history: list[dict]) -> dict:
    """State -> motion: first/last/delta over one subject+predicate series."""
    if not history:
        return {"n": 0}
    try:
        vals = [float(h.get("object", 0)) for h in history]
    except (ValueError, TypeError):
        return {"n": len(history), "numeric": False}
    return {"n": len(history), "first": vals[0], "last": vals[-1],
            "delta": round(vals[-1] - vals[0], 4),
            "span": [history[0].get("time"), history[-1].get("time")]}
