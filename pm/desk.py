"""Paper desk — confidence-gated paper trading, no execution. Ever.

Reads assessed records (human model_p and/or Jev verdicts). Policy:
  - confidence = |noul - 0.5| * 2 (distance from coin-flip).
  - ENTER paper book iff |edge| >= EDGE_MIN and confidence >= CONF_MIN.
  - Else review queue (human decides; machine never upgrades itself).
Facts go to code, judgments nag. Paper positions append-only to
data/paper/positions.jsonl. No sizing beyond fixed paper units —
no compounding claims until calibration exists.

Usage:
    python3 pm/desk.py [--edge-min 0.05] [--conf-min 0.6]
"""
from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def conf(noul):
    try:
        return abs(float(noul) - 0.5) * 2
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge-min", type=float, default=0.05)
    ap.add_argument("--conf-min", type=float, default=0.6)
    args = ap.parse_args()

    book, review = [], []
    for fp in sorted(Path(ROOT, "data", "resolutions").glob("*.json")):
        if fp.name.startswith("_"):
            continue
        try:
            r = json.loads(fp.read_text())
        except ValueError:
            continue
        cands = []
        if isinstance(r.get("model_p"), (int, float)):
            # Human assessments carry NO implicit confidence: only an
            # explicit confidence field admits them to the paper book.
            # (Default 1.0 would let vibes through the gate.)
            hc = r.get("confidence")
            cands.append(("human", r["model_p"],
                          hc if isinstance(hc, (int, float)) else 0.0))
        jv = r.get("jev_assessment") or {}
        if isinstance(jv.get("resolves_yes_noul"), (int, float)):
            cands.append(("jev", jv["resolves_yes_noul"],
                          conf(jv["resolves_yes_noul"])))
        mk = r.get("market_p")
        for judge, mp, cf in cands:
            if not isinstance(mk, (int, float)):
                continue
            edge = mp - mk
            if abs(edge) >= args.edge_min and cf >= args.conf_min:
                book.append({"slug": fp.stem,
                             "question": (r.get("question") or "")[:80],
                             "judge": judge, "model_p": mp, "market_p": mk,
                             "edge": round(edge, 3), "confidence": round(cf, 3),
                             "units": 1, "at": datetime.now(timezone.utc).isoformat()})
            else:
                review.append({"slug": fp.stem, "judge": judge,
                               "edge": round(edge, 3), "confidence": round(cf, 3),
                               "why": "below thresholds"})
    outdir = ROOT / "data" / "paper"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(outdir / "positions.jsonl", "a") as fh:
        for b in book:
            fh.write(json.dumps(b) + "\n")
    (outdir / f"review-{day}.json").write_text(json.dumps(review, indent=2))
    print(f"[DESK] paper={len(book)} review={len(review)} "
          f"(edge>={args.edge_min}, conf>={args.conf_min})")
    for b in book:
        print(f"  PAPER {b['edge']:+.3f} conf={b['confidence']} [{b['judge']}] {b['question'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
