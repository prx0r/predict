"""Assess — Jev-native valuation loop for structured records.

Takes records with model_p unset (or --all to refresh), sends each as
Jev Decisions state, records the verdict alongside — never overwriting
human assessments. Key from env OPENROUTER_API_KEY only; never stored,
never logged, never committed (see .gitignore + pre-push check).

Usage:
    OPENROUTER_API_KEY=... python3 pm/assess.py --top 5
    OPENROUTER_API_KEY=... python3 pm/assess.py --slug trump-renames-ai-by-september-30
    OPENROUTER_API_KEY=... python3 pm/assess.py --all --limit 20
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pm"))

from judge import jev_decide  # noqa: E402


def state_of(rec: dict) -> str:
    parts = [
        f"MARKET: {rec.get('question')}",
        f"Market Yes price: {rec.get('market_p')} "
        f"(bid {rec.get('bestBid')} / ask {rec.get('bestAsk')})",
        f"Volume ${rec.get('volume', 0):,.0f}, liquidity ${rec.get('liquidity', 0):,.0f}",
        f"Deadline: {rec.get('endDate')}",
        "REQUIREMENTS:",
        *[f"  - {s[:200]}" for s in rec.get("requirements", [])],
        "EXCLUSIONS:",
        *[f"  - {s[:200]}" for s in rec.get("exclusions", [])],
    ]
    alpha = rec.get("alpha") or {}
    for p in alpha.get("precedents", [])[:4]:
        parts.append(f"PRECEDENT: {p[:200]}")
    if alpha.get("crux"):
        parts.append(f"CRUX: {alpha['crux'][:250]}")
    return "\n".join(parts)


QUESTIONS = {
    "resolves_yes": {
        "type": "noul",
        "instructions": "Will this market resolve Yes?",
        "criteria": {
            "true": "A qualifying action occurs within the deadline per the requirements",
            "false": "No qualifying action, or only excluded actions occur",
        },
    },
    "conditions_misleading": {
        "type": "noul",
        "instructions": "Do the conditions materially narrow what the title suggests?",
        "criteria": {
            "true": "Exclusions carve out title-plausible scenarios",
            "false": "Title and conditions align",
        },
    },
}


def assess_file(fp: Path) -> dict | None:
    rec = json.loads(fp.read_text())
    try:
        ans = jev_decide(state_of(rec), QUESTIONS, model="typesafe/jev-1.13")
    except Exception as e:
        print(f"  [{fp.stem[:40]}] JUDGE ERR {str(e)[:100]}")
        return None
    rj = ans.get("resolves_yes", {})
    cm = ans.get("conditions_misleading", {})
    rec["jev_assessment"] = {
        "model": "typesafe/jev-1.13",
        "via": "openrouter-decisions-api",
        "resolves_yes_noul": rj.get("noul"),
        "conditions_misleading_noul": cm.get("noul"),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }
    mp = rec.get("market_p")
    jy = rj.get("noul")
    rec["edge_jev"] = round(jy - mp, 3) if isinstance(jy, (int, float)) and isinstance(mp, (int, float)) else None
    fp.write_text(json.dumps(rec, indent=2))
    print(f"  [{fp.stem[:45]}] jev_yes={jy} mislead={cm.get('noul')} edge={rec['edge_jev']}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default=None)
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    files = sorted(Path(ROOT, "data", "resolutions").glob("*.json"))
    files = [f for f in files if not f.name.startswith("_")]
    if args.slug:
        files = [Path(ROOT, "data", "resolutions", args.slug + ".json")]
    elif args.top:
        recs = []
        for f in files:
            try:
                r = json.loads(f.read_text())
            except ValueError:
                continue
            if r.get("jev_assessment"):
                continue
            recs.append((r.get("divergence", 0), f))
        recs.sort(key=lambda t: -t[0])
        files = [f for _, f in recs[:args.top]]
    elif not args.all:
        ap.error("need --slug, --top N, or --all")
    else:
        files = files[:args.limit]
    print(f"[ASSESS] {len(files)} records")
    n = 0
    for f in files:
        if assess_file(f):
            n += 1
        time.sleep(2)
    print(f"[ASSESS] {n} verdicts recorded (key never stored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
