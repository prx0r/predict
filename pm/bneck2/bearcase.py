"""Bear cases as boolean dependency trees (stdlib only).

Each target gets conditions that must go TRUE for the bear to pay.
Conditions are binary: true / false / null (unknown, never 0.5).
P(bear) = weight of TRUE / weight of RESOLVED; coverage reported separately.
Polls: price_* evaluate live via Yahoo; manual_* stay null until a human or
evidence-hunter resolves them. Trees live in bearcases.json (editable).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREES = ROOT / "data" / "bottlenecks" / "bearcases.json"
PROBS = ROOT / "data" / "bottlenecks" / "bear_probs.json"

DEFAULT_TREES = {
    "LITE": [
        {"id": "merchant_squeeze", "w": 3, "poll": "manual",
         "q": "Merchant laser supply normalizes; LITE open-market buying ends"},
        {"id": "margin_break", "w": 2, "poll": "price_vs_high",
         "ticker": "LITE", "below": 0.70,
         "q": "LITE >30% off 2y high (margin fear priced)"},
        {"id": "inP_pass", "w": 1, "poll": "manual",
         "q": "InP substrate ASP hikes passed through (AXT raises sustained)"}],
    "COHR": [
        {"id": "telemetry_shift", "w": 3, "poll": "manual",
         "q": "Hyperscaler RFPs require telemetry/predictive diagnostics"},
        {"id": "margin_break", "w": 2, "poll": "price_vs_high",
         "ticker": "COHR", "below": 0.70,
         "q": "COHR >30% off 2y high"},
        {"id": "inP_cost", "w": 1, "poll": "manual",
         "q": "InP substrate costs rise faster than module ASPs"}],
    "MRVL": [
        {"id": "bundle_win", "w": 3, "poll": "manual",
         "q": "Credo (or rival) announces bundled PIC+DSP production win displacing MRVL socket"},
        {"id": "share_loss", "w": 2, "poll": "price_vs_high",
         "ticker": "MRVL", "below": 0.70, "q": "MRVL >30% off 2y high"},
        {"id": "cpo_skip", "w": 1, "poll": "manual",
         "q": "Major CPO ramp skips pluggable DSP (architecture bypass)"}],
    "NVDA": [
        {"id": "ai_chips", "w": 2, "poll": "manual",
         "q": "AI-designed merchant silicon wins a hyperscaler socket from NVDA"},
        {"id": "share_loss", "w": 2, "poll": "price_vs_high",
         "ticker": "NVDA", "below": 0.70, "q": "NVDA >30% off 2y high"},
        {"id": "capex_cut", "w": 1, "poll": "manual",
         "q": "2+ hyperscalers cut AI capex guides same quarter"}],
    "AVGO": [
        {"id": "bom_control", "w": 3, "poll": "manual",
         "q": "Hyperscaler specifies module BOM excluding AVGO content (design loss)"},
        {"id": "share_loss", "w": 1, "poll": "price_vs_high",
         "ticker": "AVGO", "below": 0.70, "q": "AVGO >30% off 2y high"}],
    "PANW": [
        {"id": "margin_crack", "w": 3, "poll": "manual",
         "q": "Gross margin declines 2+ quarters (platform discounting)"},
        {"id": "share_loss", "w": 1, "poll": "price_vs_high",
         "ticker": "PANW", "below": 0.70, "q": "PANW >30% off 2y high"}],
    "CSCO": [
        {"id": "share_loss", "w": 2, "poll": "manual",
         "q": "Arista takes 2+ hyperscaler switching deals from CSCO"},
        {"id": "weak", "w": 1, "poll": "price_vs_high",
         "ticker": "CSCO", "below": 0.80, "q": "CSCO >20% off 2y high"}],
    "CRWD": [
        {"id": "margin_crack", "w": 3, "poll": "manual",
         "q": "Gross margin declines 2+ quarters (AI-detection commoditized)"},
        {"id": "share_loss", "w": 1, "poll": "price_vs_high",
         "ticker": "CRWD", "below": 0.70, "q": "CRWD >30% off 2y high"}],
}


def ensure() -> dict:
    if not TREES.exists():
        TREES.write_text(json.dumps(
            {"asof": "2026-09-10", "trees": DEFAULT_TREES,
             "states": {}}, indent=1))
    return json.loads(TREES.read_text())


def save(doc: dict) -> None:
    TREES.write_text(json.dumps(doc, indent=1))


def set_state(ticker: str, cond_id: str, value: bool | None,
              source: str = "") -> dict:
    doc = ensure()
    st = doc.setdefault("states", {}).setdefault(ticker, {})
    st[cond_id] = {"value": value, "source": source}
    save(doc)
    return st[cond_id]


def poll_price(cond: dict, px: dict[str, dict[str, float]]) -> bool | None:
    t = cond.get("ticker", "")
    s = px.get(t, {})
    if len(s) < 200:
        return None
    dys = sorted(s)
    hi = max(s[d] for d in dys)
    last = s[dys[-1]]
    if not hi:
        return None
    return (last / hi) < float(cond.get("below", 0.7))


def evaluate(doc: dict | None = None,
             px: dict[str, dict[str, float]] | None = None) -> dict:
    doc = doc or ensure()
    px = px if px is not None else {}
    out = {}
    for ticker, conds in doc.get("trees", {}).items():
        states = doc.get("states", {}).get(ticker, {})
        tot_w = res_w = true_w = 0
        rows = []
        for c in conds:
            w = c.get("w", 1)
            tot_w += w
            v = None
            src = "unresolved"
            if c.get("poll") == "price_vs_high" and px:
                v = poll_price(c, px)
                src = "price poll"
            st = states.get(c["id"])
            if st is not None and st.get("value") is not None:
                v = bool(st["value"])
                src = st.get("source", "manual")
            rows.append({"id": c["id"], "q": c["q"], "w": w,
                         "value": v, "source": src})
            if v is not None:
                res_w += w
                true_w += w if v else 0
        p = (true_w / res_w) if res_w else None
        out[ticker] = {"p_bear": round(p, 3) if p is not None else None,
                       "coverage": round(res_w / tot_w, 3) if tot_w else 0.0,
                       "conditions": rows}
    return out


def poll_all() -> dict:
    import sys
    sys.path.insert(0, str(ROOT))
    from bneck2 import prices as P
    doc = ensure()
    tickers = {c.get("ticker") for cs in doc.get("trees", {}).values()
               for c in cs if c.get("ticker")}
    px = {}
    for t in tickers:
        try:
            cs = P.history(t, "2y").get("closes", [])
            if len(cs) >= 200:
                px[t] = {c["date"]: c["close"] for c in cs}
        except Exception:
            pass
    probs = evaluate(doc, px)
    PROBS.write_text(json.dumps(probs, indent=1))
    return {"tickers": sorted(probs),
            "p": {t: probs[t]["p_bear"] for t in probs},
            "coverage": {t: probs[t]["coverage"] for t in probs}}
