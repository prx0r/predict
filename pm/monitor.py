"""Resolution monitor — paper-only watch loop (no execution, no disputes).

Three checks per run, alerts appended to data/watch/alerts-YYYY-MM-DD.jsonl:
 1. UMA STATUS: re-fetch tracked records; alert on any proposal/dispute
    state or status change since last run.
 2. SET-SUM DRIFT: exclusive sets (hurricane buckets, putin legs) summed
    on last-trade; alert past 0.985/1.015. Alerts are leads — verify on
    live books before any conclusion.
 3. NEW LISTINGS: mini-sweep for conditionIds not in records; alert on
    high-divergence arrivals.

State: data/watch/state.json (last statuses + known ids).
Usage:
    python3 pm/monitor.py
    python3 pm/monitor.py --sets-only
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pm"))

from resolution import structure  # noqa: E402

GAMMA = "https://gamma-api.polymarket.com"

# Exclusive sets worth summing (verified single events).
SETS = {
    "hurricane-2026": ["how many hurricanes 2026 Atlantic"],
    "putin-meet": ["Trump Putin meet next"],
}

SWEEP_QUERIES = ["Trump", "hurricane", "Fed rate", "Bitcoin", "election 2026"]


def get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": "predict-monitor"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def load_state():
    p = ROOT / "data" / "watch" / "state.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {"statuses": {}, "known_ids": []}


def save_state(st):
    d = ROOT / "data" / "watch"
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(st, indent=2))


def alert(kind: str, detail: dict, fh):
    row = {"at": datetime.now(timezone.utc).isoformat(),
           "kind": kind, **detail}
    fh.write(json.dumps(row) + "\n")
    print(f"  [ALERT:{kind}] {json.dumps(detail)[:160]}")
    return row


def check_tracked(fh, st):
    n = 0
    for fp in sorted((ROOT / "data" / "resolutions").glob("*.json")):
        if fp.name.startswith("_"):
            continue
        try:
            rec = json.loads(fp.read_text())
        except ValueError:
            continue
        slug = rec.get("slug")
        if not slug:
            continue
        try:
            doc = get(f"{GAMMA}/events/slug/{slug}")
        except Exception as e:
            print(f"  [TRACK ERR] {slug[:40]}: {str(e)[:60]}")
            continue
        for m in doc.get("markets", [doc]):
            urs = (m.get("umaResolutionStatus") or "").lower()
            key = m.get("conditionId") or slug
            prev = st["statuses"].get(key)
            if urs in ("proposed", "disputed") or (prev and prev != urs):
                alert("uma-status", {"slug": slug, "status": urs,
                                     "prev": prev,
                                     "question": (m.get("question") or "")[:80]}, fh)
                n += 1
            st["statuses"][key] = urs
    return n


def check_sets(fh):
    n = 0
    for name, queries in SETS.items():
        legs = []
        for q in queries:
            try:
                url = GAMMA + "/public-search?" + urllib.parse.urlencode({"q": q, "limit_tag": 10})
                doc = get(url)
            except Exception:
                continue
            evs = doc if isinstance(doc, list) else doc.get("events", [])
            for ev in evs:
                ms = ev.get("markets", [ev])
                if len(ms) >= 3:  # a real set, not singletons
                    legs = ms
                    break
            if legs:
                break
        if len(legs) < 3:
            continue
        tot, ps = 0.0, []
        for m in legs:
            try:
                p = float((json.loads(m.get("outcomePrices") or "[]") or [0])[0])
            except (ValueError, TypeError):
                continue
            tot += p
            ps.append(round(p, 3))
        if tot < 0.985 or tot > 1.015:
            alert("set-sum", {"set": name, "sum": round(tot, 3),
                              "legs": ps, "n": len(ps)}, fh)
            n += 1
        else:
            print(f"  [SET {name}] sum={tot:.3f} ({len(ps)} legs, inside band)")
    return n


def check_new(fh, st):
    known = set(st.get("known_ids", []))
    fresh = 0
    for fp in sorted((ROOT / "data" / "resolutions").glob("*.json")):
        if fp.name.startswith("_"):
            continue
        try:
            r = json.load(open(fp))
            if r.get("conditionId"):
                known.add(r["conditionId"])
        except ValueError:
            pass
    for q in SWEEP_QUERIES:
        try:
            url = GAMMA + "/public-search?" + urllib.parse.urlencode({"q": q, "limit_tag": 10})
            doc = get(url)
        except Exception:
            continue
        evs = doc if isinstance(doc, list) else doc.get("events", [])
        for ev in evs:
            for m in ev.get("markets", [ev]):
                cid = m.get("conditionId")
                if cid and cid not in known:
                    known.add(cid)
                    try:
                        rec = structure(m)
                    except Exception:
                        continue
                    if rec.get("divergence", 0) >= 8:
                        alert("new-listing", {"question": (m.get("question") or "")[:80],
                                             "divergence": rec["divergence"],
                                             "slug": m.get("slug")}, fh)
                        fresh += 1
    st["known_ids"] = sorted(known)
    return fresh


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets-only", action="store_true")
    args = ap.parse_args()
    st = load_state()
    d = ROOT / "data" / "watch"
    d.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    with open(d / f"alerts-{day}.jsonl", "a") as fh:
        if not args.sets_only:
            n += check_tracked(fh, st)
            n += check_new(fh, st)
        n += check_sets(fh)
    save_state(st)
    print(f"[MONITOR] {n} alerts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
