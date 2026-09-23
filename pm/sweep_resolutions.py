"""Resolution sweep — hundreds of markets in, top 50 structured records out.

Pipeline: broad Gamma queries -> dedupe by conditionId -> structure all
-> priority rank -> save top 50 JSONs + sweep stats.

Priority = complexity * (1 + log10(volume+1)) + live bonus. Complexity
rewards lawyerly text; volume rewards anyone-cares; live bonus rewards
resolvable-soon. Rationale logged in PROCESS.md, not hidden in code.

Usage:
    python3 pm/sweep_resolutions.py
    python3 pm/sweep_resolutions.py --top 50 --out data/resolutions
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pm"))

from resolution import fetch_search, structure  # noqa: E402

QUERIES = [
    "Trump", "Putin", "election 2026", "Fed rate cut", "recession",
    "CPI inflation", "unemployment", "GDP growth",
    "Bitcoin", "Ethereum", "Bitcoin $150k", "crypto reserve",
    "Super Bowl", "World Series", "NBA championship", "Champions League",
    "World Cup", "Oscars", "Nobel Peace Prize",
    "hurricane", "earthquake", "temperature record",
    "AI model", "OpenAI", "TikTok", "GTA", "iPhone",
    "SpaceX Mars", "Ukraine ceasefire", "Taiwan",
    "interest rate", "stock market record", "Olympics",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--out", default=str(ROOT / "data" / "resolutions"))
    ap.add_argument("--queries", default=",".join(QUERIES))
    args = ap.parse_args()
    queries = [q.strip() for q in args.queries.split(",") if q.strip()]

    seen, raw = {}, []
    for i, q in enumerate(queries):
        try:
            rows = fetch_search(q, limit=10)
        except Exception as e:
            print(f"  [{q}] ERR {str(e)[:80]}")
            continue
        new = 0
        for m in rows:
            cid = m.get("conditionId") or m.get("id")
            if cid and cid not in seen:
                seen[cid] = True
                raw.append(m)
                new += 1
        print(f"  [{q}] {len(rows)} fetched, {new} new")
        if i < len(queries) - 1:
            time.sleep(1)
    print(f"[SWEEP] {len(raw)} unique markets from {len(queries)} queries")

    recs = []
    for m in raw:
        try:
            recs.append(structure(m))
        except Exception as e:
            print(f"  [STRUCT ERR] {str(e)[:80]}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ranked = []
    for r in recs:
        live = 2 if ((r.get("endDate") or "")[:10] >= today
                     and (r.get("umaResolutionStatus") or "") not in ("resolved", "finalized")) else 0
        try:
            vol = float(r.get("volume") or 0)
        except (ValueError, TypeError):
            vol = 0.0
        score = r.get("complexity", 0) * (1 + math.log10(vol + 1)) + live
        ranked.append((round(score, 2), r))
    ranked.sort(key=lambda t: -t[0])

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    import re
    for score, r in ranked[:args.top]:
        slug = re.sub(r"[^a-z0-9]+", "-", ((r.get("slug") or r.get("question") or "m").lower())).strip("-")
        (outdir / f"{slug}.json").write_text(json.dumps({**r, "priority": score}, indent=2))
    stats = {"swept_at": datetime.now(timezone.utc).isoformat(),
             "queries": len(queries), "unique": len(raw),
             "structured": len(recs), "saved_top": min(args.top, len(ranked)),
             "top_scores": [(s, (r.get("question") or "")[:70]) for s, r in ranked[:10]]}
    (outdir / "_sweep_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"[SWEEP] saved top {min(args.top, len(ranked))} + stats")
    for s, r in ranked[:10]:
        print(f"  [{s}] p={r.get('market_p')} vol=${(r.get('volume') or 0):,.0f} :: {(r.get('question') or '')[:65]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
