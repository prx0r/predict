"""bneck quant — recognition gates, base rates, Tk/Td, short convexity.

RECOGNITION GATES (calibrated on data/bottlenecks/precedents.json):
  binding: spot_vs_peak>=0.85 | runup_2yr>=3 | book_to_bill>=1.2 | lead_x>=2
  crowded: thematic_vehicle + top3>0.6 | 2-star/overvalued | +100% runup narrative
  dissolution: spot<-15% (first kill) | spot<-30% (confirmed) | supply>1.5x demand
    | inventory_build | substitution_milestone | kill_ratio>=0.5

INVESTABLE QUANTITY (msg 16): which constraints can't be eliminated faster
than demand for their output grows?
  Tk = years for AI/industry to eliminate the constraint
  Td = years until demand overwhelms supply
  Td*2 <= Tk -> LONG-WINDOW | Tk <= 2 -> CLOSING | else MID

  RedundancyRisk = P(agi) * P(deploy) * purity * min(lev,2)/2 * min(yrs,10)/10
  ShortConvexity = RedundancyRisk * crowded / (1 - crowded + 0.2)

Missing readings score neutral; priors carry sparse nodes. Stdlib only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRECEDENTS_PATH = ROOT / "data" / "bottlenecks" / "precedents.json"
READINGS_GLOB = "data/bottlenecks/readings_*.json"

# Residual constraint classes -> eliminability by AGI (0 = irreducible).
CONSTRAINT_CLASSES = {
    "knowledge": 0.9,
    "human-skill": 0.9,
    "compute-architecture": 0.75,
    "physical-resources": 0.5,
    "physical-processes": 0.35,
    "ip-rights": 0.25,
    "regulatory-permission": 0.15,
}


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def base_rates(precedents: dict | None = None) -> dict:
    precedents = precedents or load_json(PRECEDENTS_PATH, {"precedents": []})
    eq, com = [], []
    for p in precedents.get("precedents", []):
        nums = [float(x) for x in re.findall(r"~?-(\d+(?:\.\d+)?)%", p.get("drawdown", ""))]
        if not nums:
            continue
        worst = max(nums)
        if re.search(r"/kg|carbonate|spot|NAND", p.get("drawdown", ""), re.I):
            com.append(worst)
        eq.append(worst)

    def med(xs):
        xs = sorted(xs)
        return round(xs[len(xs) // 2], 1) if xs else 0.0

    return {"median_equity_unwind_pct": med(eq),
            "median_commodity_unwind_pct": med(com),
            "n": len(precedents.get("precedents", []))}


def _wmean(pairs: list[tuple[float | None, float]]) -> float:
    num = sum(v * w for v, w in pairs if v is not None)
    den = sum(w for v, w in pairs if v is not None)
    return num / den if den else 0.5


def binding_score(node: dict, reading: dict | None = None) -> dict:
    r = reading or {}
    spot = r.get("spot_vs_peak")
    runup = r.get("price_runup_2yr")
    btb = r.get("book_to_bill")
    lead = r.get("lead_time_x")
    vehicle = 0.7 if r.get("thematic_vehicle") else None
    comps = [
        (min(1.0, spot / 0.85) if spot is not None else None, 0.3),
        (min(1.0, runup / 3.0) if runup is not None else None, 0.2),
        (min(1.0, btb / 1.2) if btb is not None else None, 0.2),
        (min(1.0, lead / 2.0) if lead is not None else None, 0.15),
        (vehicle, 0.15),
    ]
    read_score = _wmean(comps)
    prior = float(node.get("prevalence") if node.get("prevalence") is not None else 0.5)
    return {"binding": round(0.6 * prior + 0.4 * read_score, 3),
            "from_readings": round(read_score, 3), "prior": prior}


def dissolution_score(node: dict, reading: dict | None = None,
                      triggered: list[str] | None = None) -> dict:
    r = reading or {}
    trig = set(triggered or [])
    kills = node.get("kill_signals", [])
    kill_ratio = (sum(1 for k in kills if k in trig) / len(kills)) if kills else 0.0
    spot = r.get("spot_vs_peak")
    spot_break = max(0.0, min(1.0, (0.85 - spot) / 0.35)) if spot is not None else None
    supply = r.get("supply_response")
    glut = min(1.0, max(0.0, (supply - 1.0) / 1.0)) if supply is not None else None
    sub = 1.0 if r.get("substitution_milestone") else (0.0 if "substitution_milestone" in r else None)
    inv = 1.0 if r.get("inventory_build") else (0.0 if "inventory_build" in r else None)
    comps = [(kill_ratio, 0.35), (spot_break, 0.25), (glut, 0.2), (sub, 0.1), (inv, 0.1)]
    d = _wmean(comps) if any(v is not None for v, _ in comps) else kill_ratio
    return {"dissolution": round(d, 3), "kill_ratio": round(kill_ratio, 3)}


def tk_td(node: dict) -> dict:
    """The investable quantity: can demand outrun elimination?"""
    tk, td = node.get("tk_years"), node.get("td_years")
    if tk is None or td is None:
        return {"tk": tk, "td": td, "signal": "UNKNOWN"}
    if td * 2 <= tk:
        sig = "LONG-WINDOW"
    elif tk <= 2:
        sig = "CLOSING"
    else:
        sig = "MID"
    return {"tk": tk, "td": td, "signal": sig}


def redundancy_risk(node: dict) -> float:
    """P(agi)*P(deploy)*purity*leverage*years — rent destruction probability mass."""
    agi = float(node.get("agi_p") if node.get("agi_p") is not None else 0.3)
    dep = float(node.get("deploy_p") if node.get("deploy_p") is not None else 0.5)
    pur = float(node.get("revenue_purity") if node.get("revenue_purity") is not None else 0.5)
    lev = min(float(node.get("op_leverage") if node.get("op_leverage") is not None else 1.0), 2.0) / 2.0
    yrs = min(float(node.get("expect_years") if node.get("expect_years") is not None else 5.0), 10.0) / 10.0
    return round(agi * dep * pur * lev * yrs, 4)


def short_convexity(node: dict) -> float:
    """RedundancyRisk * crowded / (1 - crowded + 0.2): monster-trade ranker."""
    crowded = float(node.get("crowdedness") if node.get("crowdedness") is not None else 0.5)
    return round(redundancy_risk(node) * crowded / (1 - crowded + 0.2), 4)


def regime(node: dict, reading: dict | None = None,
           triggered: list[str] | None = None) -> dict:
    b = binding_score(node, reading)["binding"]
    d = dissolution_score(node, reading, triggered)["dissolution"]
    crowded = float(node.get("crowdedness") if node.get("crowdedness") is not None else 0.5)
    status = node.get("status", "latent")
    if status == "solved" or d >= 0.8:
        reg = "EXIT"
    elif status == "binding" and (triggered or d >= 0.4):
        reg = "SHORT_WATCH"
    elif status == "binding" and (d >= 0.2 or crowded >= 0.7):
        reg = "DISSOLUTION_WATCH"
    elif status == "binding" and crowded < 0.5 and b >= 0.55:
        reg = "OVERWEIGHT"
    elif status == "binding":
        reg = "HOLD"
    elif status == "emerging" and b >= 0.5 and crowded < 0.5:
        reg = "ACCUMULATE"
    elif status == "emerging":
        reg = "WATCH"
    else:
        reg = "IGNORE"
    tktd = tk_td(node)
    return {"regime": reg, "binding": b, "dissolution": d, "crowdedness": crowded,
            "status": status, "tk_td": tktd["signal"],
            "redundancy": redundancy_risk(node), "convexity": short_convexity(node)}


def score_all(graph: dict, readings: dict[str, dict] | None = None,
              triggered: dict[str, list[str]] | None = None) -> list[dict]:
    readings, triggered = readings or {}, triggered or {}
    out = []
    for node in graph.get("nodes", []):
        r = regime(node, readings.get(node["id"]), triggered.get(node["id"], []))
        out.append({"id": node["id"], "label": node["label"], **r,
                    "tickers": node.get("tickers", [])})
    order = {"EXIT": 0, "SHORT_WATCH": 1, "DISSOLUTION_WATCH": 2, "OVERWEIGHT": 3,
             "HOLD": 4, "ACCUMULATE": 5, "WATCH": 6, "IGNORE": 7}
    out.sort(key=lambda x: (order.get(x["regime"], 9), -x["binding"]))
    return out


def load_readings(root: Path = ROOT) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for path in sorted(root.glob(READINGS_GLOB)):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in doc.get("readings", []):
            nid = entry.get("node_id")
            if not nid:
                continue
            prev = merged.get(nid, {})
            if entry.get("date", "") >= prev.get("date", ""):
                merged[nid] = entry
    return merged
