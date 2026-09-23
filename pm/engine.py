"""Engine — outcomes in, scores out. Two modes, one honesty standard.

SCORE (live book): re-fetch each assessed record in data/resolutions/,
resolve outcome (1/0/None) + dispute flag from Gamma/UMA fields, and
report Brier(model) vs Brier(market), edge-sign hit rate, calibration
buckets. Writes data/engine/report-<date>.json. Never edits records.

BACKTEST (ranker validation): fetch recently-resolved markets, structure
them, and test whether divergence predicted dispute occurrence. This is
the claim the whole sweep rests on — run it before trusting the ranker.

Usage:
    python3 pm/engine.py score
    python3 pm/engine.py backtest --queries "Trump,Biden,election,Fed" --limit 8
"""
from __future__ import annotations

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
UMA_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/umaprotocol/uma-polygon"


def outcome_of(m: dict):
    """(outcome, disputed) from a live market object. None = unresolved.

    NOTE: umaResolutionStatuses is a status HISTORY — every resolution
    passes through "proposed", so its mere presence means nothing.
    Disputed = an explicit disputed marker anywhere in the trail."""
    urs = (m.get("umaResolutionStatus") or "").lower()
    trail = " ".join(str(x) for x in (m.get("umaResolutionStatuses") or []))
    disputed = urs == "disputed" or "disput" in trail.lower()
    try:
        px = json.loads(m.get("outcomePrices") or "[]")
        p = float(px[0]) if px else None
    except (ValueError, TypeError):
        p = None
    if urs in ("resolved", "finalized") and p is not None:
        return (1 if p > 0.5 else 0), disputed
    if p in (0.0, 1.0) and (m.get("closed") or m.get("archived")):
        return (int(p), disputed)
    return None, disputed


def brier(p, outcome):
    return (p - outcome) ** 2 if isinstance(p, (int, float)) else None


def cmd_score() -> int:
    recs = []
    for f in sorted((ROOT / "data" / "resolutions").glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            recs.append(json.loads(f.read_text()))
        except ValueError:
            continue
    assessed = [r for r in recs if isinstance(r.get("model_p"), (int, float))]
    print(f"[ENGINE] {len(recs)} records, {len(assessed)} assessed")
    rows, mb, kb, hits, n_hit = [], [], [], 0, 0
    for r in assessed:
        m = fetch_one(r)
        if not m:
            rows.append({"question": r.get("question"), "status": "unresolved"})
            continue
        oc, dis = outcome_of(m)
        try:
            mk = float((json.loads(m.get("outcomePrices") or "[]") or [None])[0])
        except (ValueError, TypeError):
            mk = None
        row = {"question": (r.get("question") or "")[:80],
               "model_p": r["model_p"], "market_then": r.get("market_p"),
               "market_now": mk, "outcome": oc, "disputed": dis,
               "edge_then": r.get("edge")}
        if oc is not None:
            bm, bk = brier(r["model_p"], oc), brier(mk if mk is not None else r.get("market_p"), oc)
            row["brier_model"] = bm
            row["brier_market"] = bk
            if bm is not None:
                mb.append(bm)
            if bk is not None:
                kb.append(bk)
            e = r.get("edge")
            if e and oc is not None:
                n_hit += 1
                if (e > 0 and oc == 1) or (e < 0 and oc == 0):
                    hits += 1
        rows.append(row)
    rep = {"scored_at": datetime.now(timezone.utc).isoformat(),
           "n_assessed": len(assessed), "n_resolved": len(mb),
           "mean_brier_model": sum(mb) / len(mb) if mb else None,
           "mean_brier_market": sum(kb) / len(kb) if kb else None,
           "edge_hit_rate": hits / n_hit if n_hit else None,
           "rows": rows}
    outdir = ROOT / "data" / "engine"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"report-{day}.json").write_text(json.dumps(rep, indent=2))
    print(f"  resolved: {len(mb)} | Brier model={rep['mean_brier_model']} market={rep['mean_brier_market']} | edge hits {hits}/{n_hit}")
    print(f"[SAVED] data/engine/report-{day}.json")
    return 0


def fetch_one(rec: dict):
    slug = rec.get("slug")
    urls = []
    if slug:
        urls += [f"{GAMMA}/events/slug/{slug}", f"{GAMMA}/markets/slug/{slug}"]
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "predict-engine"})
            doc = json.load(urllib.request.urlopen(req, timeout=20))
            ms = doc.get("markets", [doc]) if isinstance(doc, dict) else doc
            cid = rec.get("conditionId")
            for m in ms:
                if not cid or m.get("conditionId") == cid:
                    return m
            return ms[0] if ms else None
        except Exception:
            continue
    return None


def cmd_backtest(queries, limit) -> int:
    import time
    markets = []
    for q in queries:
        url = GAMMA + "/public-search?" + urllib.parse.urlencode({"q": q, "limit_tag": limit})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "predict-engine"})
            doc = json.load(urllib.request.urlopen(req, timeout=20))
            evs = doc if isinstance(doc, list) else doc.get("events", [])
            for ev in evs:
                markets.extend(ev.get("markets", [ev]))
        except Exception as e:
            print(f"  [{q}] ERR {str(e)[:80]}")
        time.sleep(1)
    seen, rows = set(), []
    for m in markets:
        cid = m.get("conditionId") or m.get("id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        oc, dis = outcome_of(m)
        if oc is None:
            continue  # backtest needs resolved outcomes only
        try:
            rec = structure(m)
        except Exception:
            continue
        rows.append((rec, oc, dis))
    print(f"[BACKTEST] {len(rows)} resolved markets with structure")
    if len(rows) < 20:
        print("  thin sample — rerun with more queries")
        return 0
    rows.sort(key=lambda t: t[0].get("divergence", 0))
    q = max(1, len(rows) // 4)
    print("  quartile: n, dispute_rate, mean_divergence")
    out_q = []
    for i in range(4):
        part = rows[i * q:(i + 1) * q] if i < 3 else rows[i * q:]
        if not part:
            continue
        dr = sum(1 for _, _, d in part if d) / len(part)
        md = sum(t[0].get("divergence", 0) for t in part) / len(part)
        out_q.append({"quartile": i + 1, "n": len(part),
                      "dispute_rate": round(dr, 3), "mean_divergence": round(md, 2)})
        print(f"  Q{i+1}: n={len(part)} dispute_rate={dr:.3f} mean_div={md:.2f}")
    outdir = ROOT / "data" / "engine"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"backtest-{day}.json").write_text(json.dumps(
        {"ran_at": datetime.now(timezone.utc).isoformat(),
         "n": len(rows), "quartiles": out_q,
         "note": "tests whether divergence predicts dispute occurrence"}, indent=2))
    print(f"[SAVED] data/engine/backtest-{day}.json")
    return 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["score", "backtest"])
    ap.add_argument("--queries", default="Trump,Biden,election,Fed rate,BTC,hurricane,Nobel")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()
    if args.mode == "score":
        return cmd_score()
    return cmd_backtest([s.strip() for s in args.queries.split(",") if s.strip()], args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
