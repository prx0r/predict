#!/usr/bin/env python3
"""bneck status — ranked board + quant regimes + dissolution board.

Usage:
    /usr/bin/python3 scripts/status.py [--quant] [--trigger node:"signal" ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import graph as G
from bneck2 import prices as P
from bneck2 import quant as Q
from bneck2 import belief as B


def belief_board(root: Path) -> str:
    """Disagreement board from data/beliefs/claims.json (may not exist yet)."""
    import json
    path = root / "data" / "beliefs" / "claims.json"
    try:
        claims = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ("# Belief board — no claims yet\n"
                "Add data/beliefs/claims.json: [{id, edge_id, text, p, clock,\n"
                " author, ts, origin_claim_id, derived_from[], meta}]\n"
                "Clocks: hard | expert | pm | equity.")
    by_edge: dict[str, list] = {}
    for c in claims:
        by_edge.setdefault(c.get("edge_id", "?"), []).append(c)
    lines = ["# Belief board — disagreement across clocks"]
    for edge_id, group in sorted(by_edge.items()):
        split = B.clock_split(group)
        d = B.disagreement(split)
        lines.append(f"## {edge_id}: pooled={B.combine(group)['p']:.2f} "
                     f"({B.combine(group)['n_independent']} independent)")
        for clock, s in split.items():
            lines.append(f"   {clock:7} {s['p']:.2f} (n={s['n']}, indep={s['n_independent']})")
        for flag in d["flags"]:
            lines.append(f"   !! {flag}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quant", action="store_true", help="append quant regime table")
    ap.add_argument("--belief", action="store_true", help="append disagreement board")
    ap.add_argument("--trigger", action="append", default=[])
    args = ap.parse_args()
    triggered: dict[str, list[str]] = {}
    for item in args.trigger:
        if ":" not in item:
            print(f"bad --trigger (need node:signal): {item}", file=sys.stderr)
            return 1
        nid, sig = item.split(":", 1)
        triggered.setdefault(nid.strip(), []).append(sig.strip())

    g = G.load_graph()
    tickers = sorted({t for n in g["nodes"] for t in n.get("tickers", [])})
    moves = P.get_moves(tickers)
    readings = Q.load_readings()
    rows = Q.score_all(g, readings, triggered)
    convexity = {r["id"]: r["convexity"] for r in rows}
    print(G.render(g, moves, triggered, convexity))
    if args.quant:
        print("# Quant regimes — Tk/Td + RedundancyRisk + ShortConvexity + Criticality")
        crit = G.criticality(g)
        for r in rows:
            print(f"{r['regime']:17} b={r['binding']:.2f} d={r['dissolution']:.2f} "
                  f"tk/td={r.get('tk_td')} red={r['redundancy']:.3f} conv={r['convexity']:.3f} "
                  f"crit={crit.get(r['id'], 0):.2f}  {r['label'][:40]}")
        print(f"\nBase rates: {Q.base_rates()}")
        top = sorted(crit.items(), key=lambda kv: -kv[1])[:5]
        print("Most critical (N-1 removal): " + ", ".join(f"{k}={v:.2f}" for k, v in top))
    if args.belief:
        print(belief_board(ROOT))
    print(f"(priced {len(moves)}/{len(tickers)} from 5-min $0 cache)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
