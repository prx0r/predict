#!/usr/bin/env python3
"""killfeed loop — collect (optional live) -> evaluate -> verdict-log.

Usage:
    /usr/bin/python3 scripts/killfeed.py            # offline: coverage check
    /usr/bin/python3 scripts/killfeed.py --live     # poll SEC/OpenAlex/PM
    /usr/bin/python3 scripts/killfeed.py --live --max-nodes 3 --no-write

Live collection is best-effort per node (collectors never raise); verdicts
append to data/beliefs/kill_observations.jsonl with measured-vs-threshold
rows, INCLUDING non-firings. Promotion to kill_signals stays in updater/gates.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import killfeed as K


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--max-nodes", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    summary = K.run(live=args.live, write=not args.no_write,
                    max_nodes=args.max_nodes)
    print(K.render_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
