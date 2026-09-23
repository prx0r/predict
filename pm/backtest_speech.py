"""E8 backtest — "find sure things": two mechanical strategies on the
speech-count family, no probability model.

A. Narrative fade (cross-sectional, conservative fill):
   Within one event's word-count family, any Yes leg priced far above
   its siblings is narrative money, not word-count money. Buy No at
   that leg's LAST trade price (a price you may not have been able to
   get — the real fill would be at the peak premium, which is higher,
   so the P&L below is a floor, not a ceiling).

B. Repricing lag (needs intraday depth): does the market still sit
   cheap AFTER the event ends? If repricing is minutes, E8's long leg
   is dead; if hours, the transcript counter has a fill.

Usage:
    python3 pm/backtest_speech.py
    python3 pm/backtest_speech.py --lag-conditions 0xabc 0xdef
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"
FEE = 0.0075  # per leg, notional, E7 assumption

QUERIES = [
    "Trump say State of the Union",
    "Biden say State of the Union",
    "Trump say Ribbon Cutting",
    "Trump say Energy Innovation Summit",
    "Trump say inaugural",
    "Trump say address",
    "Biden say address",
    "Trump say debate",
    "Trump say interview",
    "Trump say press conference",
]


def get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "predict-backtest"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def pull_families() -> dict:
    """event key -> list of legs {q, p_yes, last, outcome, end}."""
    fams: dict = {}
    seen_q: set = set()
    for q in QUERIES:
        url = f"{GAMMA}/public-search?" + urllib.parse.urlencode({"q": q, "limit_tag": 6})
        try:
            doc = get(url)
        except Exception as e:
            print(f"  [{q}] ERR {str(e)[:60]}")
            continue
        for ev in (doc if isinstance(doc, list) else doc.get("events", [])):
            ms = ev.get("markets") or []
            legs = []
            for m in ms:
                qn = (m.get("question") or "")
                if "say" not in qn.lower() or qn in seen_q:
                    continue
                if (m.get("umaResolutionStatus") or "").lower() not in ("resolved", "finalized"):
                    continue
                try:
                    p = float(json.loads(m.get("outcomePrices") or "[]")[0])
                except (ValueError, TypeError, IndexError):
                    continue
                seen_q.add(qn)
                legs.append({"q": qn, "last": float(m.get("lastTradePrice") or 0),
                             "yes": 1 if p > 0.5 else 0,
                             "end": (m.get("endDate") or "")[:10]})
            if len(legs) >= 8:
                fams[f"{ev.get('title', '')[:52]} | {legs[0]['end']}"] = legs
        time.sleep(0.8)
    return fams


def backtest_fade(fams: dict, mult: float = 4.0, floor: float = 0.05) -> dict:
    """Flag = Yes price far above family median (narrative premium).
    Trade = buy the NO token at (1 - yes_price). Win pays 1, so pnl is
    +yes_price on a No win and -(1 - yes_price) on a Yes win. The 98%
    No base rate makes hit rate meaningless — ROI vs the fade-all
    baseline is the only honest comparison."""
    rows = []
    for name, legs in sorted(fams.items()):
        prices = [l["last"] for l in legs]
        med = statistics.median(prices)
        thr = max(floor, med * mult, med + floor)
        for l in legs:
            if l["last"] >= thr:
                yes_p = l["last"]
                no_cost = 1 - yes_p
                fee = no_cost * FEE
                pnl = (1 - no_cost) if l["yes"] == 0 else -no_cost
                rows.append({"family": name, "q": l["q"][:60], "yes_fill": yes_p,
                             "no_cost": round(no_cost, 4), "thr": round(thr, 4),
                             "med": med, "won": l["yes"] == 0,
                             "pnl": round(pnl - fee, 4)})
    wins = sum(r["won"] for r in rows)
    pnl = sum(r["pnl"] for r in rows)
    staked = sum(r["no_cost"] for r in rows)
    return {"legs_flagged": len(rows), "wins": wins,
            "hit_rate": round(wins / len(rows), 3) if rows else None,
            "staked": round(staked, 3), "pnl": round(pnl, 3),
            "roi": round(pnl / staked, 3) if staked else None, "rows": rows}


def baseline_fade_all(fams: dict) -> dict:
    """Buy No on EVERY leg at (1 - last Yes price). The confound test:
    speech families are ~97% No, so this wins on hit rate too. If the
    screen doesn't beat this on ROI, the screen is worthless."""
    pnl = staked = n = wins = 0.0
    for legs in fams.values():
        for l in legs:
            no_cost = 1 - l["last"]
            if no_cost <= 0.001:
                continue
            n += 1
            won = l["yes"] == 0
            wins += won
            pnl += (1 - no_cost if won else -no_cost) - no_cost * FEE
            staked += no_cost
    return {"legs": int(n), "wins": int(wins),
            "hit_rate": round(wins / n, 3) if n else None,
            "staked": round(staked, 2), "pnl": round(pnl, 2),
            "roi": round(pnl / staked, 3) if staked else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mult", type=float, default=4.0)
    ap.add_argument("--lag-conditions", nargs="*", default=[])
    args = ap.parse_args()

    fams = pull_families()
    n_legs = sum(len(v) for v in fams.values())
    base = baseline_fade_all(fams)
    print(f"[PULL] {len(fams)} speech families, {n_legs} resolved legs")
    print(f"[BASE] fade-all: n={base['legs']} hit={base['hit_rate']} "
          f"pnl={base['pnl']} roi={base['roi']}")
    print("[SWEEP] mult x floor -> flagged / wins / roi")
    for mult in (3.0, 4.0, 6.0, 1000.0):
        line = []
        for floor in (0.03, 0.05, 0.10):
            r = backtest_fade(fams, mult=mult, floor=floor)
            line.append(f"f{floor}: {r['legs_flagged']}/{r['wins']}w roi={r['roi']}")
        print(f"  mult={mult:<7} " + "  ".join(line))
    res = backtest_fade(fams, mult=args.mult)
    print(f"[FADE] flagged={res['legs_flagged']} wins={res['wins']} "
          f"hit={res['hit_rate']} staked={res['staked']} pnl={res['pnl']} roi={res['roi']}")
    for r in sorted(res["rows"], key=lambda x: -x["yes_fill"]):
        print(f"  yes={r['yes_fill']:5.2f} no@={r['no_cost']:5.3f} thr={r['thr']:5.2f} "
              f"med={r['med']:4.2f} {'W' if r['won'] else 'L'} pnl={r['pnl']:+6.3f}  {r['q']}")

    out = {"ran_at": datetime.now(timezone.utc).isoformat(),
           "fee_assumption": FEE, "params": {"mult": args.mult},
           "families": {k: len(v) for k, v in fams.items()},
           "baseline_fade_all": base,
           "fade": {k: v for k, v in res.items() if k != "rows"},
           "rows": res["rows"]}
    p = ROOT / "data" / "engine" / f"backtest_speech_{datetime.now(timezone.utc):%Y-%m-%d}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"[SAVED] {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
