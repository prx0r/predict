"""Threat triage — price-damage check per death-watch name (stdlib).

For each THREATENS target: forward return vs SPY since first threat date +
max drawdown. Buckets: CONFIRMED-DYING (threat + damage), QUESTIONED
(threat but thriving — researcher may be wrong), UNPRICED (flat).
Triage is prioritization, not validation. Writes threat_queue.json.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bneck2 import prices as P  # noqa: E402

OVERLAY = ROOT / "data" / "bottlenecks" / "threat_graph.json"
OUT = ROOT / "data" / "bottlenecks" / "threat_queue.json"


def _series(ticker: str) -> dict[str, float]:
    try:
        return {c["date"]: c["close"]
                for c in P.history(ticker, "2y").get("closes", [])}
    except Exception:
        return {}


def main() -> dict:
    ov = json.loads(OVERLAY.read_text())
    spy = _series("SPY")
    rows = []
    for e in ov.get("edges", []):
        tick = e["target"].replace("CO_", "", 1)
        dates = [q.get("date", "")[:10] for q in e.get("evidence", []) if q.get("date")]
        first = min([d for d in dates if d] or ["2026-08-01"])
        px = _series(tick)
        if len(px) < 60:
            rows.append({"ticker": tick, "status": "NO-DATA",
                         "first_threat": first})
            continue
        dys = sorted(d for d in px if d >= first)
        sds = sorted(d for d in spy if d >= first)
        if len(dys) < 20 or len(sds) < 20:
            rows.append({"ticker": tick, "status": "NO-DATA",
                         "first_threat": first})
            continue
        r = px[dys[-1]] / px[dys[0]] - 1 if px[dys[0]] else 0.0
        sr = spy[sds[-1]] / spy[sds[0]] - 1 if spy[sds[0]] else 0.0
        peak, mdd = px[dys[0]], 0.0
        for d in dys:
            peak = max(peak, px[d])
            mdd = min(mdd, px[d] / peak - 1 if peak else 0.0)
        excess = r - sr
        status = ("DYING" if excess < -0.15 else
                  "QUESTIONED" if excess > 0.10 else "UNPRICED")
        rows.append({"ticker": tick, "status": status,
                     "first_threat": first,
                     "excess": round(excess, 4), "maxdd": round(mdd, 4),
                     "by": sorted({q.get("source", "").replace("feedify:", "")
                                    for q in e.get("evidence", [])})[:3]})
    order = {"DYING": 0, "UNPRICED": 1, "QUESTIONED": 2, "NO-DATA": 3}
    rows.sort(key=lambda x: (order.get(x["status"], 9), x.get("excess", 0)))
    OUT.write_text(json.dumps(
        {"asof": datetime.date.today().isoformat(), "queue": rows}, indent=1))
    summ = {k: sum(1 for r in rows if r["status"] == k) for k in order}
    return {"n": len(rows), "buckets": summ,
            "dying": [r["ticker"] for r in rows if r["status"] == "DYING"][:10],
            "questioned": [r["ticker"] for r in rows if r["status"] == "QUESTIONED"][:10]}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
