"""Set-sum backtest — replay trentmkelly book ladders, measure the edge.

Question: how often did exclusive buckets sum away from $1, at what
size, on live books (not last-trade)? v1 measures opportunity
frequency + depth; P&L join on resolved sets comes second (needs
winners, queried separately).

Sets are defined by event slug (tokens resolved live via Gamma).
Books: trentmkelly 5-min depth runs, selective dates, filtered to set
tokens only. Disk-light by construction.

Usage:
    python3 pm/backtest_arb.py --days 2026-08-01,2026-08-15,2026-09-01 --runs-per-day 12
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
HF_FILE = ("https://huggingface.co/datasets/trentmkelly/"
           "polymarket_historical_data/resolve/main/{path}")
HF_API = "https://huggingface.co/api/datasets/trentmkelly/polymarket_historical_data"
GAMMA = "https://gamma-api.polymarket.com"

SETS = {
    # slug -> note (tokens resolved live; must be single-event buckets)
    "hurricane-2026": "0/1-3/4-6/7+ buckets (verify event)",
}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "predict-backtest"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def event_tokens(slug: str) -> list:
    """Event slug -> clobTokenIds. Verified join: book asset_id uses the
    same 75-78 digit scheme (pull_books.py matched 4 tokens / 2645 rows).
    Do NOT use Gamma numeric ids or market_id (different schemes)."""
    doc = json.loads(get(f"{GAMMA}/events/slug/{slug}"))
    toks = []
    for m in doc.get("markets", [doc] if isinstance(doc, dict) else []):
        try:
            toks.extend(json.loads(m.get("clobTokenIds") or "[]"))
        except (ValueError, TypeError):
            continue
    return [str(t) for t in toks]


def runs_for_day(day: str, per_day: int):
    doc = json.loads(get(HF_API, timeout=30).decode())
    files = sorted(s["rfilename"] for s in doc.get("siblings", [])
                   if f"/order_book_depth/date={day}/" in s["rfilename"])
    if not files:
        return []
    step = max(1, len(files) // per_day)
    return files[::step][:per_day]


def book_sum(parquet_path: Path, tokens: set):
    """Per-token best bid/ask from one depth run -> set sum over tokens present."""
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    t = pq.read_table(str(parquet_path))
    t = t.filter(pc.is_valid(t.column("asset_id")))
    t = t.filter(pc.is_in(t.column("asset_id").cast("string"),
                          pa_array(sorted(tokens))))
    bids, asks = {}, {}
    for r in t.to_pylist():
        try:
            price, size = float(r["price"]), float(r["size"])
        except (ValueError, TypeError):
            continue
        tok = str(r["asset_id"])
        if r["side"] == "bid":
            bids[tok] = max(bids.get(tok, 0), price)
        else:
            asks[tok] = min(asks.get(tok, 1e9), price) if tok in asks else price
    return bids, asks


def pa_array(vals):
    import pyarrow as pa
    return pa.array(vals)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", default="",
                    help="comma dates YYYY-MM-DD (default: 6 sample days over 60d)")
    ap.add_argument("--runs-per-day", type=int, default=12)
    ap.add_argument("--sets", default=",".join(SETS))
    args = ap.parse_args()
    if args.days:
        days = [d.strip() for d in args.days.split(",")]
    else:
        from datetime import timedelta
        today = datetime.now(timezone.utc).date()
        days = [(today - timedelta(days=d)).isoformat() for d in (3, 10, 17, 24, 31, 45)]

    tmp = ROOT / "data" / "_tmp_backtest"
    tmp.mkdir(parents=True, exist_ok=True)
    set_tokens = {}
    for slug in [s.strip() for s in args.sets.split(",") if s.strip()]:
        try:
            set_tokens[slug] = event_tokens(slug)
            print(f"  [SET {slug}] {len(set_tokens[slug])} tokens")
        except Exception as e:
            print(f"  [SET {slug}] ERR {str(e)[:80]}")
    events = []
    for day in days:
        try:
            runs = runs_for_day(day, args.runs_per_day)
        except Exception as e:
            print(f"  [{day}] listing ERR {str(e)[:60]}")
            continue
        for rel in runs:
            lp = tmp / Path(rel).name
            raw = None
            for attempt in range(3):
                try:
                    raw = get(HF_FILE.format(path=rel), timeout=120)
                    break
                except Exception as e:
                    print(f"  [RETRY {rel.split('/')[-1]} try {attempt+1}] {str(e)[:60]}")
                    time.sleep(3 * (attempt + 1))
            if raw is None:
                print(f"  [SKIP {rel.split('/')[-1]}] download failed 3x")
                continue
            try:
                lp.write_bytes(raw)
                for slug, toks in set_tokens.items():
                    bids, asks = book_sum(lp, set(toks))
                    if len(bids) + len(asks) < 2:
                        continue
                    # buy-basket cost (asks) vs sell-basket proceeds (bids)
                    buy = sum(asks.get(t, 1.0) for t in toks if t in asks)
                    sell = sum(bids.get(t, 0.0) for t in toks if t in bids)
                    events.append({"day": day, "run": lp.name, "set": slug,
                                   "n_legs": len(set(toks) & (set(bids) | set(asks))),
                                   "buy_sum": round(buy, 4), "sell_sum": round(sell, 4)})
            except Exception as e:
                print(f"  [SKIP {rel.split('/')[-1]}] {str(e)[:70]}")
            finally:
                lp.unlink(missing_ok=True)
    devs = [abs(e["buy_sum"] - 1.0) for e in events] + [abs(e["sell_sum"] - 1.0) for e in events]
    outdir = ROOT / "data" / "engine"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"arb-backtest-{stamp}.json").write_text(json.dumps(
        {"ran_at": datetime.now(timezone.utc).isoformat(), "events": events,
         "n_runs": len(events),
         "max_dev": round(max(devs), 4) if devs else None,
         "mean_dev": round(sum(devs) / len(devs), 4) if devs else None,
         "past_015": sum(1 for d in devs if d > 0.015),
         "past_03": sum(1 for d in devs if d > 0.03)}, indent=2))
    print(f"[ARB-BACKTEST] {len(events)} run-sets, max_dev={max(devs) if devs else None}, "
          f"past_1.5c={sum(1 for d in devs if d > 0.015)}, past_3c={sum(1 for d in devs if d > 0.03)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
