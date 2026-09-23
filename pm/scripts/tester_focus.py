#!/usr/bin/env python3
"""Focused NVDA/OpenAI tester — the NORTHSTAR-2 initial battery.

Runs every NVDA/OpenAI-relevant experiment + the signal board for the
focus universe, one report. Usage:
  /usr/bin/python3 scripts/tester_focus.py [--live]
--live refreshes the biweekly panel first (slow, network-heavy).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FOCUS = ["E001", "E004", "E010", "E011", "E012", "E014", "E015", "E016",
         "E017", "E018", "E019", "E020", "E021", "E022", "E023", "E024"]


def main() -> int:
    from bneck2 import experiments as X
    from bneck2 import lab as LAB
    if "--live" in sys.argv[1:]:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_predict_panel.py"),
                        "--biweekly"], check=False)
    print("# FOCUS battery — NVDA/OpenAI/BTC + acq chain + lead-lag")
    for hid in FOCUS:
        fn = X.REGISTRY.get(hid)
        if not fn:
            print(f"  {hid}: missing");
            continue
        try:
            result, verdict, n = fn()
        except Exception as exc:
            result, verdict, n = {"error": str(exc)[:150]}, "INCONCLUSIVE", 0
        LAB.receipt(hid, result, verdict, n,
                      comparisons=int(result.get("comparisons", 1)))
        LAB.run_file(hid, {"fn": hid, "mode": "focus"}, result)
        flag = " [directional-only]" if n < 30 else ""
        print(f"  {hid}: {verdict}{flag} n={n}")
    print(LAB.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
