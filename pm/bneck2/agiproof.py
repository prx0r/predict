"""AGI-proof rating — how well a company survives AGI (stdlib only).

Score 0-100 from structural features (never prices):
  + complement (ProphetMap aiContribution 0-1): up to +25
  + moat (moatCapture 0-5): (moat/5)*25
  - substitution (death-watch threat negatives): -8 each, cap -30
  - labor arbitrage (sells text-labor by unit): -20
Base 50. Grades A>=80 B>=65 C>=50 D>=35 else F.
Re-run as threats/scores update = continually updating rating.
Job-automation graphs are the proxy logic: Eloundou-style exposure applied
to what the company SELLS, not who it employs.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# sells human cognitive labor by the unit (body-count + papers)
LABOR_ARB = {"CHGG", "FVRR", "UPWK", "FIVN", "CNXC", "FRSH", "DHX", "RHI",
             "PAYX", "MAN", "KFY", "HSII"}


def components(ticker: str) -> dict:
    try:
        uni = json.loads((ROOT / "third_party" / "prophetmap" / "data" / "universe.json").read_text())
        us = uni if isinstance(uni, list) else uni.get("tickers", [])
        pm = next((u for u in us if u.get("symbol") == ticker), {})
    except OSError:
        pm = {}
    try:
        threats = json.load(open(ROOT / "data" / "bottlenecks" / "threats.json"))
        neg = threats.get(ticker, {}).get("negatives", 0)
        by = threats.get(ticker, {}).get("researchers", [])
    except OSError:
        neg, by = 0, []
    ai = pm.get("aiContribution")
    moat = pm.get("moatCapture")
    return {"ai": ai, "moat": moat, "negatives": neg, "by": by,
            "labor_arb": ticker in LABOR_ARB,
            "layer": pm.get("layer", "")}


def rate(ticker: str) -> dict:
    c = components(ticker)
    score = 50.0
    reasons = []
    if c["ai"] is not None:
        score += 25 * float(c["ai"])
        reasons.append(f"complement +{25 * float(c['ai']):.0f} (aiContribution {c['ai']})")
    if c["moat"] is not None:
        score += 25 * (float(c["moat"]) / 5)
        reasons.append(f"moat +{25 * float(c['moat']) / 5:.0f} (capture {c['moat']}/5)")
        if float(c["moat"]) <= 1:
            score -= 10
            reasons.append("weak-moat penalty -10")
    if c["negatives"]:
        pen = min(8 * c["negatives"], 30)
        score -= pen
        reasons.append(f"substitution -{pen} ({c['negatives']} researcher negatives)")
    if c["labor_arb"]:
        score -= 20
        reasons.append("labor-arbitrage -20 (sells cognition by unit)")
    score = round(max(0.0, min(100.0, score)), 1)
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D" if score >= 35 else "F"
    return {"ticker": ticker, "score": score, "grade": grade,
            "reasons": reasons, "components": c,
            "watch": [f for f in
                      (["substitution pressure rising"] if c["negatives"] >= 2 else [])
                      + (["labor model directly in AGI path"] if c["labor_arb"] else [])
                      + (["thin moat"] if c["moat"] is not None and float(c["moat"]) <= 1 else [])]}


def board(tickers: list[str]) -> list[dict]:
    out = [rate(t) for t in tickers]
    return sorted(out, key=lambda r: r["score"])
