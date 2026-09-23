#!/usr/bin/env python3
"""Build the prediction panel (slow, network-heavy, cached where set).

Saves data/predict/panel-<yyyymm>.jsonl rows for the trailing 12 monthly
windows. Reruns overwrite the month file (idempotent per date+ticker).
Usage: /usr/bin/python3 scripts/build_predict_panel.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from bneck2 import predict as PD
    freq = "biweekly" if "--biweekly" in sys.argv else "monthly"
    prefix = "biwk-" if freq == "biweekly" else "panel-"
    rows = PD.build_panel(freq=freq)
    outdir = ROOT / "data" / "predict"
    outdir.mkdir(parents=True, exist_ok=True)
    by_date: dict[str, list[dict]] = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
    for d, rs in sorted(by_date.items()):
        (outdir / f"{prefix}{d}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rs) + "\n", encoding="utf-8")
    good = sum(1 for r in rows if r.get("fwd_20") is not None)
    print(f"panel: {len(rows)} rows over {len(by_date)} months, "
          f"{good} with forwards "
          f"({datetime.now(timezone.utc).strftime('%H:%M:%S')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
