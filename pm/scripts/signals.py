#!/usr/bin/env python3
"""Signal board — current composite scores ranked by evidence lower bound.

Score = per-date composite (train-signed winners). Rank key = score, but
every line carries the factor IC Wilson lower bounds so nothing reads
stronger than its evidence. Directional until temporal validation matures.
Usage: /usr/bin/python3 scripts/signals.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from bneck2 import predict as PD
    files = sorted((ROOT / "data" / "predict").glob("panel-*.jsonl"))
    rows = []
    for f in files:
        rows += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    if not rows:
        print("no monthly panel; run scripts/build_predict_panel.py")
        return 1
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 3, 0)]
    train = [r for r in rows if r["date"] < cut]
    cur = [r for r in rows if r["date"] == dates[-1]]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 20]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    lo = {s["factor"]: s["hit_lo"] for s in scr}
    scored = PD.composite_by_date(cur, winners or ["f_mom_20"], signs)
    print("# Signal board — composite score + evidence lower bounds "
          "(directional)")
    print(f"winners={winners or ['f_mom_20 fallback']} "
          f"asof={dates[-1]} threshold=IC>0.1")
    for r in sorted(scored, key=lambda x: -x["score"]):
        ev = ",".join(f"{f}:{lo.get(f, 0):.2f}" for f in (winners or ["f_mom_20"]))
        print(f"  {r['score']:+.3f} {r['ticker']:9} fwd={r.get('fwd_20')} [{ev}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
