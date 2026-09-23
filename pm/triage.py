"""Triage — Jev classifies what the regex ranker cannot.

For records without verdicts: choice (game_type) + score (attention)
via Jev, one call each (cheap). Compares against regex divergence and
logs disagreements — ranker-vs-judge deltas are themselves signal
(the regex found template noise last time; the judge may miss what
regex catches).

Output: data/watch/triage-<date>.json ranked by attention. Paper only.

Usage:
    OPENROUTER_API_KEY=... python3 pm/triage.py --top 10
    OPENROUTER_API_KEY=... python3 pm/triage.py --all --limit 30
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
from assess import state_of, JEV_MODEL_PIN  # noqa: E402

TRIAGE_QUESTIONS = {
    "game_type": {
        "type": "choice",
        "instructions": "Which game does this market belong to?",
        "criteria": {
            "arb": "mechanical mispricing vs related markets",
            "decay": "time-decay toward a knowable outcome",
            "judgment": "genuinely uncertain event, research wins",
            "noise": "resolved, thin, or unplayable",
        },
    },
    "attention": {
        "type": "score",
        "instructions": "How urgently does this deserve human review?",
        "criteria": ["ignore", "watch", "review soon", "review now"],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    files = sorted(Path(ROOT, "data", "resolutions").glob("*.json"))
    files = [f for f in files if not f.name.startswith("_")]
    recs = []
    for f in files:
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        if r.get("jev_assessment"):
            continue
        recs.append((r.get("divergence", 0), f, r))
    recs.sort(key=lambda t: -t[0])
    if args.top:
        recs = recs[:args.top]
    elif not args.all:
        ap.error("need --top N or --all")
    else:
        recs = recs[:args.limit]

    print(f"[TRIAGE] {len(recs)} unassessed records")
    queue, deltas = [], []
    for _, f, r in recs:
        try:
            ans = jev_decide(state_of(r), TRIAGE_QUESTIONS, model=JEV_MODEL_PIN)
        except Exception as e:
            print(f"  [{f.stem[:40]}] ERR {str(e)[:80]}")
            continue
        gt, at = ans.get("game_type", {}), ans.get("attention", {})
        entry = {"slug": f.stem, "question": (r.get("question") or "")[:80],
                 "market_p": r.get("market_p"), "divergence": r.get("divergence"),
                 "game_type": gt.get("choice"), "attention": at.get("score"),
                 "judge": JEV_MODEL_PIN}
        queue.append(entry)
        # Ranker-vs-judge delta: regex says look (high div), judge says noise.
        if r.get("divergence", 0) >= 8 and gt.get("choice") == "noise":
            deltas.append({"slug": f.stem, "divergence": r.get("divergence"),
                           "note": "regex-flagged, judge-dismissed"})
            print(f"  [DELTA] {f.stem[:45]} div={r.get('divergence')} but judge=noise")
        time.sleep(2)
    queue.sort(key=lambda e: (-(e.get("attention") or 0), -(e.get("divergence") or 0)))
    outdir = ROOT / "data" / "watch"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"triage-{day}.json").write_text(json.dumps(
        {"ran_at": datetime.now(timezone.utc).isoformat(),
         "queue": queue, "deltas": deltas}, indent=2))
    print(f"[TRIAGE] {len(queue)} triaged, {len(deltas)} deltas (key never stored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
