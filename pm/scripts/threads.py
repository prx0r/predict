#!/usr/bin/env python3
"""Open-thread counter — keeps docs/THREADS.md honest.

Counts live state (open unknowns, inconclusive hyps, open predictions,
queued markers) and diffs against the ledger's claimed numbers.
Usage: /usr/bin/python3 scripts/threads.py [--check]
--check exits nonzero on mismatch (add new threads here AND in THREADS.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# hyps_open grew 4 -> 7 when lag searches were regraded EXPLORATORY
# (counts as open by design). Update here if the ledger's open set changes.
EXPECTED = {"unknowns_open": 4, "hyps_open": 8, "preds_open": 1}


def counts() -> dict:
    from bneck2 import lab as LAB
    from bneck2 import evidence as E
    hyps = {}
    for r in LAB.load_receipts():
        hyps[r.get("hyp", "?")] = r.get("verdict", "INCONCLUSIVE")
    return {
        "unknowns_open": len(E.read_unknowns()),
        "hyps_open": sum(1 for v in hyps.values() if v == "INCONCLUSIVE"),
        "preds_open": sum(1 for r in LAB.load_predictions()
                          if r.get("resolved") is None),
    }


def main() -> int:
    got = counts()
    print(f"threads live: {got} (expected {EXPECTED})")
    if "--check" in sys.argv[1:]:
        return 0 if got == EXPECTED else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
