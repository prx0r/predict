#!/usr/bin/env python3
"""bneck poll — 5-min $0 price snapshot -> data/prices_latest.json (+ history).

Usage:
    /usr/bin/python3 scripts/poll.py
Cron:
    */5 * * * * cd /home/ubuntu/bneck2 && /usr/bin/python3 scripts/poll.py >> /tmp/bneck2-prices.log 2>&1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2.prices import snapshot

HIST = ROOT / "data" / "prices.jsonl"
LATEST = ROOT / "data" / "prices_latest.json"


def main() -> int:
    snap = snapshot()
    HIST.parent.mkdir(parents=True, exist_ok=True)
    with open(HIST, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap) + "\n")
    LATEST.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    ok = sum(1 for v in snap["tickers"].values() if "price" in v)
    ionq = snap["tickers"].get("IONQ", {})
    print(f"{snap['ts']} ok={ok}/{len(snap['tickers'])} IONQ={ionq.get('price')} {ionq.get('pct_1d')}%")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
