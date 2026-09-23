"""Pattern scan — resolved markets with hard win conditions, judged by Jev.

For each resolved market: structure the text, ask Jev whether the
conditions are confusing/misleading, then test for patterns (dispute
markers, price extremes, category clustering). Answers whether
confusing language predicts anything — the historical counterpart to
the live divergence ranker.

Usage:
    OPENROUTER_API_KEY=... python3 pm/pattern_scan.py --queries "Trump,Biden,election" --limit 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pm"))

from judge import jev_decide  # noqa: E402
from resolution import structure  # noqa: E402

JEV_MODEL = "typesafe/jev-1.13"

READ_QS = {
    "confusing": {
        "type": "noul",
        "instructions": "Would a careful reader find these win conditions confusing or ambiguous?",
        "criteria": {"true": "Multiple plausible readings, vague terms, or unclear thresholds",
                     "false": "Single clear reading a non-expert would get right"},
    },
    "title_misleading": {
        "type": "noul",
        "instructions": "Does the title suggest something different from what the conditions actually require?",
        "criteria": {"true": "Title implies an easier/different bar than the text enforces",
                     "false": "Title faithfully summarizes the conditions"},
    },
}


def state_of(rec: dict) -> str:
    parts = [f"QUESTION: {rec.get('question')}",
             f"RESOLVED: {'Yes' if rec.get('_outcome') == 1 else 'No'}",
             "REQUIREMENTS:"]
    parts += [f"  - {s[:200]}" for s in rec.get("requirements", [])]
    parts += ["EXCLUSIONS:"]
    parts += [f"  - {s[:200]}" for s in rec.get("exclusions", [])]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="Trump,Biden,election,Fed rate,ceasefire,Nobel,hurricane,BTC")
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    seen, recs = set(), []
    for q in [s.strip() for s in args.queries.split(",") if s.strip()]:
        url = ("https://gamma-api.polymarket.com/public-search?"
               + urllib.parse.urlencode({"q": q, "limit_tag": args.limit}))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "predict-pattern"})
            doc = json.load(urllib.request.urlopen(req, timeout=25))
        except Exception as e:
            print(f"  [{q}] ERR {str(e)[:70]}")
            continue
        evs = doc if isinstance(doc, list) else doc.get("events", [])
        for ev in evs:
            for m in ev.get("markets", [ev]):
                cid = m.get("conditionId")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                urs = (m.get("umaResolutionStatus") or "").lower()
                try:
                    px = json.loads(m.get("outcomePrices") or "[]")
                    p = float(px[0]) if px else None
                except (ValueError, TypeError):
                    p = None
                oc = None
                if urs in ("resolved", "finalized") and p is not None:
                    oc = 1 if p > 0.5 else 0
                if oc is None:
                    continue  # resolved only: need outcomes for patterns
                try:
                    rec = structure(m)
                except Exception:
                    continue
                rec["_outcome"] = oc
                rec["_disputed"] = "disput" in " ".join(
                    str(x) for x in (m.get("umaResolutionStatuses") or [])).lower()
                recs.append(rec)
        time.sleep(1)
    print(f"[PATTERN] {len(recs)} resolved structured records")

    for r in recs:
        try:
            ans = jev_decide(state_of(r), READ_QS, model=JEV_MODEL)
            r["read_confusing"] = (ans.get("confusing") or {}).get("noul")
            r["read_misleading"] = (ans.get("title_misleading") or {}).get("noul")
        except Exception as e:
            print(f"  [JUDGE ERR] {str(e)[:70]}")
            r["read_confusing"] = r["read_misleading"] = None
        time.sleep(2)

    scored = [r for r in recs if r.get("read_confusing") is not None]
    out = []
    for r in scored:
        out.append({"question": (r.get("question") or "")[:70],
                    "outcome": r.get("_outcome"),
                    "disputed": r.get("_disputed"),
                    "confusing": r.get("read_confusing"),
                    "misleading": r.get("read_misleading"),
                    "divergence": r.get("divergence")})
    # Pattern tests.
    import statistics as _s
    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 3) if xs else None
    dis = [r for r in scored if r.get("_disputed")]
    print(f"  disputed: {len(dis)}/{len(scored)}")
    print(f"  mean confusing: disputed={mean([r.get('read_confusing') for r in dis])} "
          f"clean={mean([r.get('read_confusing') for r in scored if not r.get('_disputed')])}")
    print(f"  mean misleading: disputed={mean([r.get('read_misleading') for r in dis])} "
          f"clean={mean([r.get('read_misleading') for r in scored if not r.get('_disputed')])}")
    outdir = ROOT / "data" / "patterns"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"readability-{day}.json").write_text(json.dumps(
        {"ran_at": datetime.now(timezone.utc).isoformat(), "n": len(scored),
         "records": out}, indent=2))
    print(f"[SAVED] data/patterns/readability-{day}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
