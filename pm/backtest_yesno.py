"""YES/NO backtest — per-market basket sums on live books.

Every binary market is its own exclusive set: YES_ask + NO_ask < 1.0
is a locked spread (minus 0.75%/leg fees + gas). Replays trentmkelly
5-min ladders: for each covered market, each run, record the basket
sums. Answers: how often, how deep, at what size.

Market universe comes from the books themselves (top-100 covered),
resolved via Gamma /markets/{id} (cached). No sweep needed.

Usage:
    python3 pm/backtest_yesno.py --days 2026-09-20,2026-09-21,2026-09-22 --runs-per-day 12
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF_FILE = ("https://huggingface.co/datasets/trentmkelly/"
           "polymarket_historical_data/resolve/main/{path}")
HF_API = "https://huggingface.co/api/datasets/trentmkelly/polymarket_historical_data"
GAMMA = "https://gamma-api.polymarket.com"


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "predict-backtest"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def runs_for_day(day: str, per_day: int):
    doc = json.loads(get(HF_API, timeout=30).decode())
    files = sorted(s["rfilename"] for s in doc.get("siblings", [])
                   if f"/order_book_depth/date={day}/" in s["rfilename"])
    if not files:
        return []
    step = max(1, len(files) // per_day)
    return files[::step][:per_day]


def resolve_market(mid: str):
    doc = json.loads(get(f"{GAMMA}/markets/{mid}"))
    try:
        toks = json.loads(doc.get("clobTokenIds") or "[]")
        outs = json.loads(doc.get("outcomes") or '["Yes","No"]')
    except (ValueError, TypeError):
        return None
    if len(toks) < 2:
        return None
    return {"id": mid, "question": (doc.get("question") or "")[:80],
            "yes": toks[0] if outs[0] == "Yes" else toks[1],
            "no": toks[1] if outs[0] == "Yes" else toks[0],
            "volume": doc.get("volume")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", default="")
    ap.add_argument("--runs-per-day", type=int, default=12)
    args = ap.parse_args()
    if args.days:
        days = [d.strip() for d in args.days.split(",")]
    else:
        from datetime import timedelta
        today = datetime.now(timezone.utc).date()
        days = [(today - timedelta(days=d)).isoformat() for d in (1, 3, 5, 8, 12)]

    tmp = ROOT / "data" / "_tmp_backtest"
    tmp.mkdir(parents=True, exist_ok=True)
    markets, events = {}, []
    import time as _t
    for day in days:
        try:
            runs = runs_for_day(day, args.runs_per_day)
        except Exception as e:
            print(f"  [{day}] listing ERR {str(e)[:60]}")
            continue
        for rel in runs:
            lp = tmp / Path(rel).name
            for attempt in range(3):
                try:
                    lp.write_bytes(get(HF_FILE.format(path=rel), timeout=120))
                    break
                except Exception as e:
                    print(f"  [RETRY {rel.split('/')[-1]}] {str(e)[:60]}")
                    _t.sleep(3 * (attempt + 1))
            else:
                print(f"  [SKIP {rel.split('/')[-1]}] download failed 3x")
                continue
            try:
                import pyarrow.parquet as pq
                import pyarrow.compute as pc
                t = pq.read_table(str(lp))
                mids = set(str(x) for x in t.column("market_id").to_pylist() if x)
                for mid in mids:
                    if mid not in markets:
                        try:
                            m = resolve_market(mid)
                            markets[mid] = m
                        except Exception:
                            markets[mid] = None
                        _t.sleep(0.4)
                best = {}
                for r in t.to_pylist():
                    try:
                        p = float(r["price"])
                    except (ValueError, TypeError):
                        continue
                    k = (str(r["asset_id"]), r["side"])
                    if r["side"] == "bid":
                        best[k] = max(best.get(k, 0.0), p)
                    else:
                        best[k] = min(best.get(k, 1.0), p)
                for mid, m in markets.items():
                    if not m:
                        continue
                    ya = best.get((m["yes"], "ask"))
                    na = best.get((m["no"], "ask"))
                    yb = best.get((m["yes"], "bid"))
                    nb = best.get((m["no"], "bid"))
                    if ya is None or na is None:
                        continue
                    events.append({"day": day, "run": lp.name, "mid": mid,
                                   "q": m["question"][:60], "buy_sum": round(ya + na, 4),
                                   "sell_sum": round(yb + nb, 4) if yb and nb else None})
            except Exception as e:
                print(f"  [SKIP {rel.split('/')[-1]}] {str(e)[:70]}")
            finally:
                lp.unlink(missing_ok=True)
    n = len(events)
    devs = [abs(e["buy_sum"] - 1.0) for e in events]
    print(f"[YESNO-BACKTEST] {n} market-runs, {len([m for m in markets.values() if m])} markets mapped")
    if devs:
        import statistics as _s
        print(f"  buy_sum: min={min(e['buy_sum'] for e in events):.3f} mean_dev={sum(devs)/len(devs):.4f} "
              f"past_1.5c={sum(1 for d in devs if d>0.015)} past_3c={sum(1 for d in devs if d>0.03)}")
        top = sorted(events, key=lambda e: abs(e["buy_sum"] - 1.0), reverse=True)[:8]
        print("  widest:")
        for e in top:
            print(f"    {e['buy_sum']:.3f}/{e['sell_sum']} :: {e['q'][:60]} ({e['day']})")
    outdir = ROOT / "data" / "engine"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"yesno-backtest-{stamp}.json").write_text(json.dumps(
        {"ran_at": datetime.now(timezone.utc).isoformat(), "events": events}, indent=2))
    print(f"[SAVED] data/engine/yesno-backtest-{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
