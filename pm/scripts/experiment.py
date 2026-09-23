#!/usr/bin/env python3
"""Experiment CLI — list / run / report (cg-flow; receipts canonical)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import experiments as X
from bneck2 import lab as LAB


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for hid in sorted(X.REGISTRY):
            last = LAB.load_receipts(hid)
            tail = f"{last[-1]['verdict']}" if last else "never-run"
            print(f"  {hid}: last={tail} runs={len(last)}")
        return 0
    if cmd == "report":
        print(LAB.report())
        return 0
    if cmd == "run":
        which = sys.argv[2] if len(sys.argv) > 2 else "all"
        ids = sorted(X.REGISTRY) if which == "all" else [which]
        for hid in ids:
            fn = X.REGISTRY.get(hid)
            if not fn:
                print(f"unknown {hid}")
                return 1
            try:
                result, verdict, n = fn()
            except Exception as exc:
                result, verdict, n = {"error": str(exc)[:200]}, "INCONCLUSIVE", 0
            row = LAB.receipt(hid, result, verdict, n,
                comparisons=int(result.get("comparisons", 1)))
            LAB.run_file(hid, {"fn": hid}, result,
                         ts=row["ts"], code_refs={"suite": "tests"})
            flag = " [directional-only]" if row["directional_only"] else ""
            print(f"{hid}: {verdict}{flag} n={n}")
        return 0
    print("usage: experiment.py [list|run E001|run all|report]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
