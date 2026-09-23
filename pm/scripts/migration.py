#!/usr/bin/env python3
"""Scarcity-migration board — severity, velocity, cross-world exposure,
release probability, bottleneck derivatives, consistency arbitrage.

Usage:
    /usr/bin/python3 scripts/migration.py [--record TS]
    --record appends current severities to severity_history.jsonl so dB/dt
    compounds across passes (killfeed --live calls this automatically).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import consistency as CY
from bneck2 import atoms as A
from bneck2 import evidence as E
from bneck2 import graph as G
from bneck2 import migration as M
from bneck2 import quant as Q
from bneck2 import worlds as W


def main() -> int:
    record_ts = ""
    if "--record" in sys.argv:
        i = sys.argv.index("--record")
        record_ts = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
    g = G.load_graph()
    readings = Q.load_readings()
    rows = Q.score_all(g, readings)
    hist = M.load_history()

    print("# Scarcity severity B + velocity dB/dt (top accelerators first)")
    table = []
    for r in rows:
        node = next(n for n in g["nodes"] if n["id"] == r["id"])
        sev = M.severity(node, readings.get(r["id"]))
        if record_ts:
            M.record_severity(r["id"], sev["B"], record_ts)
            hist.append({"ts": record_ts, "node_id": r["id"], "B": sev["B"]})
        vel = M.velocity(r["id"], hist)
        rel = M.release_probability(r["id"], E.read_kill_observations(r["id"]))
        table.append((vel["dB_dt"], r["id"], sev["B"], vel["accel"],
                      rel["P_release"]))
    for d, nid, b, a, rel in sorted(table, key=lambda t: -t[0])[:8]:
        print(f"  dB/dt={d:+.3f} B={b:.3f} accel={a:+.3f} "
              f"P_release={rel:.2f}  {nid}")

    doc = W.load_worlds()
    print("\n# Cross-world exposure X (need-weighted, ours distribution)")
    xs = sorted((M.cross_world_exposure(i, doc["worlds"])
                 for i in doc.get("incumbents", [])),
                key=lambda r: -r["X"])
    for x in xs:
        print(f"  X={x['X']:.3f}  {x['incumbent']}")

    print("\n# Bottleneck derivatives (what binds next if relieved)")
    for nid in [r["id"] for r in rows if r["regime"] in ("OVERWEIGHT", "HOLD")][:5]:
        deriv = M.bottleneck_derivative(nid, g)
        names = ", ".join(f"{d['node']}({d['via']})" for d in deriv[:4])
        print(f"  {nid} -> {names or 'terminal (no downstream)'}")

    print()
    print(CY.render(CY.find_inconsistencies(doc)))

    print("\n# AI-to-Atoms screen (convexity shapes, NOT a buy list)")
    sev_by = {r["id"]: M.severity(
        next(n for n in g["nodes"] if n["id"] == r["id"]),
        readings.get(r["id"]))["B"] for r in rows}
    crowd_by = {r["id"]: float(r.get("crowdedness", 0.0)) for r in rows}
    for a in A.screen(severity_by_node=sev_by, crowded=crowd_by)[:10]:
        print(f"  {a['convexity']:.3f} {a['ticker']:9} [{a['layer']}] "
              f"{','.join(a['nodes'][:3])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
