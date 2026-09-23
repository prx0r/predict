#!/usr/bin/env python3
"""Backfill the walk-forward panel honestly.

Scores are RECONSTRUCTED from the current graph (deterministic function of
node fields: binding - dissolution per node -> tickers) and each row carries
the graph sha + reconstructed:true for audit. Forwards are REAL Yahoo
closes. A backtest on this panel tests whether *today's scoring logic*
would have worked historically — valid; what it does NOT test is whether
past graph versions (different fields) would have. Rerun after graph edits.

Usage: /usr/bin/python3 scripts/backfill_panel.py [--weeks 12]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    weeks = 12
    if "--weeks" in sys.argv:
        weeks = int(sys.argv[sys.argv.index("--weeks") + 1])
    from bneck2 import backtest as BT
    from bneck2 import graph as G
    from bneck2 import quant as Q

    gpath = ROOT / "data" / "bottlenecks" / "graph_v2.json"
    sha = hashlib.sha256(gpath.read_bytes()).hexdigest()[:12]
    g = G.load_graph()
    rows = Q.score_all(g, Q.load_readings())
    scores = {}
    for r in rows:
        node = next(n for n in g["nodes"] if n["id"] == r["id"])
        for t in node.get("tickers", []):
            if t.isupper() and len(t) <= 12 and "." not in t and "-" not in t:
                scores[t] = round(r["binding"] - r["dissolution"], 3)
    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(weeks=w)).isoformat() for w in range(weeks, 0, -1)]
    panel = BT.load_panel()
    have = {(r.get("date"), r.get("ticker")) for r in panel}
    new_rows = []
    for d in dates:
        for t, s in sorted(scores.items()):
            if (d, t) not in have:
                new_rows.append({"date": d, "ticker": t, "score": s,
                                 "forward_return": None, "reconstructed": True,
                                 "graph_sha": sha})
    if new_rows:
        BT.PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BT.PANEL_PATH, "a", encoding="utf-8") as f:
            for r in new_rows:
                f.write(json.dumps(r) + "\n")
    filled = BT.fill_forwards(days=5)
    res = BT.live_result()
    print(f"backfill: +{len(new_rows)} reconstructed rows ({sha}), "
          f"+{filled} forwards filled -> {res.get('status')}: "
          f"{res.get('sharpe', res.get('need', ''))} "
          f"periods={res.get('periods', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
