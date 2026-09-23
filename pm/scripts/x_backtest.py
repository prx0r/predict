#!/usr/bin/env python3
"""X-call backtest — extractor + next-trading-day outcomes + baselines.

BEAR August playbook ported to equities: classify (direction/tickers, no
defaults) -> one outcome per event x ticker at 1d/5d/20d, SPY-adjusted ->
baselines (always-long, SPY, momentum) -> Wilson CIs -> source cards.
Usage: /usr/bin/python3 scripts/x_backtest.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
XDIR = ROOT / "data" / "x"


def next_trading(closes: dict[str, float], d: str, offset: int = 1) -> str | None:
    ds = sorted(dd for dd in closes if dd >= d)
    return ds[offset] if len(ds) > offset else None


def main() -> int:
    from bneck2 import prices as P
    from bneck2 import xextract as XE
    cards = {}
    all_ev = []
    for f in sorted(XDIR.glob("hist_*.json")):
        handle = f.stem.replace("hist_", "")
        tweets = json.loads(f.read_text(encoding="utf-8"))
        evs = []
        for t in tweets:
            c = XE.classify(str(t.get("text", "")))
            if c["kind"] != "DIRECTIONAL" or c["tickers"] == ["UNKNOWN"]:
                continue
            tickers = [x for x in c["tickers"]
                       if x in ("NVDA", "AMD", "AVGO", "MU", "INTC", "MSFT",
                                "GOOGL", "AMZN", "META", "ARM", "MRVL", "ANET",
                                "TSM", "LRCX", "AMAT", "KLAC", "COHR", "LITE",
                                "ONTO", "FORM")]
            if not tickers:
                continue
            evs.append({"date": XE._ts(t), "dir": c["direction"],
                        "tickers": tickers[:3], "id": t.get("id", "")})
        cards[handle] = {"n_calls": len(evs)}
        all_ev += [(handle, e) for e in evs]
    print(f"events: {len(all_ev)}")
    # outcomes
    cache: dict[str, dict] = {}
    spy = {c["date"]: c["close"]
           for c in P.history("SPY", "6mo").get("closes", [])}
    rows = []
    for handle, e in all_ev:
        for t in e["tickers"]:
            if t not in cache:
                cache[t] = {c["date"]: c["close"]
                            for c in P.history(t, "6mo").get("closes", [])}
            cl = cache[t]
            d1 = next_trading(cl, e["date"], 1)
            d5 = next_trading(cl, e["date"], 5)
            d20 = next_trading(cl, e["date"], 20)
            d0 = next((dd for dd in sorted(cl) if dd >= e["date"]), None)
            if not (d0 and d1 and d5 and d20):
                continue
            sgn = +1 if e["dir"] == "LONG" else -1
            for tag, dd in (("d1", d1), ("d5", d5), ("d20", d20)):
                r = sgn * (cl[dd] - cl[d0]) / cl[d0]
                sm = sorted(dd for dd in spy if dd >= e["date"])
                sp = ((spy[sm[min(5, len(sm) - 1)]] - spy[sm[0]]) / spy[sm[0]]
                      if len(sm) > 5 and spy[sm[0]] else 0.0) if tag != "d1" else 0.0
                rows.append({"handle": handle, "ticker": t, "horizon": tag,
                             "ret": round(r, 4), "spy_adj": round(r - sp, 4)})
    out = XDIR / "x_outcomes.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    # cards + summary by handle/horizon
    from collections import defaultdict
    by = defaultdict(list)
    for r in rows:
        by[(r["handle"], r["horizon"])].append(r["ret"])
    print(f"outcomes: {len(rows)}")
    for (h, z) in sorted(by):
        v = by[(h, z)]
        hit = sum(1 for x in v if x > 0) / len(v)
        print(f"  {h:16} {z}: n={len(v):3} hit={hit:.2f} mean={sum(v)/len(v):+.3%}")
    (XDIR / "cards.json").write_text(json.dumps(
        {h: {"n_calls": cards[h]["n_calls"],
             "n_outcomes": sum(1 for r in rows if r["handle"] == h)}
         for h in cards}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
