"""Mirror backtest — would following specialists + divergence filter have paid?

For each tracked wallet: pull Data API trades, resolve each market's
outcome (Gamma; resolved only), join our divergence score where the
market is tracked, and score two strategies:
  A) blind mirror (same side, 1 paper unit, 0.75%/leg fees)
  B) filtered mirror (skip where divergence >= threshold)

Reports hit rate, paper P&L, and what the filter excluded (hits and
misses both — a filter that only excludes losers is lying).

Usage:
    python3 pm/backtest_mirror.py --wallets 0x4f1d..,0x2005.. --limit 200
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

from resolution import structure  # noqa: E402

DATA_API = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
FEE = 0.0075  # taker per leg (ASSUMPTION — V2 feeType varies per
# market: Gamma carries takerBaseFee/feeSchedule/feeType per market,
# captured per row below for later refinement; units TBD, do not convert)


def get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "predict-backtest"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def wallet_trades(addr: str, limit: int, offset: int = 0):
    out = []
    while len(out) < limit:
        url = (f"{DATA_API}/trades?user={addr}&limit={min(500, limit - len(out))}"
               f"&offset={offset + len(out)}")
        try:
            batch = get(url)
        except Exception as e:
            print(f"  [TRADES ERR] {str(e)[:70]}")
            break
        if not batch:
            break
        out.extend(batch)
        offset += len(batch)
        if len(batch) < 100:
            break
        time.sleep(0.5)
    return out[:limit]


def resolve_market(condition_id: str, slug: str = ""):
    """Outcome 1/0/None + resolution text for divergence scoring.
    Slug-first (exact event lookup); public-search cannot query by
    conditionId (verified: returns unrelated markets)."""
    if slug:
        try:
            doc = get(f"{GAMMA}/events/slug/{slug}")
            for m in doc.get("markets", [doc] if isinstance(doc, dict) else []):
                if (m.get("conditionId") or "").lower() == condition_id.lower():
                    return _outcome_from(m)
        except Exception:
            pass
    return None


def _outcome_from(m: dict):
    urs = (m.get("umaResolutionStatus") or "").lower()
    try:
        px = json.loads(m.get("outcomePrices") or "[]")
        p = float(px[0]) if px else None
    except (ValueError, TypeError):
        p = None
    oc = None
    if urs in ("resolved", "finalized") and p is not None:
        oc = 1 if p > 0.5 else 0
    return {"outcome": oc, "market": m}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallets", required=True)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--offset", type=int, default=0,
                    help="skip N most-recent trades (older trades = more resolved)")
    ap.add_argument("--div-threshold", type=float, default=8.0)
    args = ap.parse_args()

    all_rows, excluded = [], []
    wallet_stats = {}
    for addr in [a.strip() for a in args.wallets.split(",") if a.strip()]:
        trades = wallet_trades(addr, args.limit, args.offset)
        print(f"  [{addr[:10]}] {len(trades)} trades")
        # Net positions per market: aggregate scale-ins/outs, VWAP entry,
        # majority side. One scored row per (wallet, market), not per fill.
        positions = {}
        for t in trades:
            cid = t.get("conditionId", "")
            if not cid:
                continue
            try:
                price, size = float(t.get("price") or 0), float(t.get("size") or 0)
            except (ValueError, TypeError):
                continue
            if not price or not size:
                continue
            p = positions.setdefault(cid, {"buy_n": 0.0, "sell_n": 0.0,
                                           "buy_sz": 0.0, "sell_sz": 0.0,
                                           "slug": t.get("slug", "")})
            if (t.get("side") or "BUY").upper() == "BUY":
                p["buy_n"] += price * size
                p["buy_sz"] += size
            else:
                p["sell_n"] += price * size
                p["sell_sz"] += size
        for cid, p in positions.items():
            res = resolve_market(cid, p.get("slug", ""))
            if not res or res["outcome"] is None:
                continue
            try:
                rec = structure(res["market"])
            except Exception:
                continue
            buy, sell = p["buy_n"], p["sell_n"]
            if buy >= sell:
                side = "BUY"
                entry = p["buy_n"] / p["buy_sz"] if p["buy_sz"] else 0
                pnl = (1.0 if res["outcome"] == 1 else 0.0) - entry * (1 + FEE)
            else:
                side = "SELL"
                entry = p["sell_n"] / p["sell_sz"] if p["sell_sz"] else 0
                pnl = entry * (1 - FEE) if res["outcome"] == 0 else -(1.0 - entry) - entry * FEE
            row = {"wallet": addr[:10], "question": (res["market"].get("question") or "")[:70],
                   "side": side, "entry": round(entry, 4),
                   "gross_usd": round(buy + sell, 2),
                   "outcome": res["outcome"],
                   "divergence": rec.get("divergence", 0),
                   "fee_type": res["market"].get("feeType"),
                   "taker_base_fee": res["market"].get("takerBaseFee"),
                   "pnl": round(pnl, 4)}
            (all_rows if rec.get("divergence", 0) < args.div_threshold else excluded).append(row)
            ws = wallet_stats.setdefault(addr[:10], {"wins": 0, "n": 0, "pnl": 0.0})
            ws["n"] += 1
            ws["pnl"] += pnl
            if pnl > 0:
                ws["wins"] += 1
            time.sleep(0.3)
    def stats(rows):
        if not rows:
            return {"n": 0}
        wins = sum(1 for r in rows if r["pnl"] > 0)
        return {"n": len(rows), "hit_rate": round(wins / len(rows), 3),
                "pnl": round(sum(r["pnl"] for r in rows), 2),
                "mean_edge": round(sum(r["pnl"] for r in rows) / len(rows), 4)}
    rep = {"ran_at": datetime.now(timezone.utc).isoformat(),
           "div_threshold": args.div_threshold,
           "mirror_all": stats(all_rows),
           "excluded_by_filter": stats(excluded),
           "excluded_sample": excluded[:10],
           "wallets": {w: {**s, "hit_rate": round(s["wins"] / s["n"], 3),
                           "pnl": round(s["pnl"], 2)}
                       for w, s in wallet_stats.items()},
           "rows": all_rows}
    outdir = ROOT / "data" / "engine"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (outdir / f"mirror-backtest-{day}.json").write_text(json.dumps(rep, indent=2))
    print(f"[MIRROR] n={rep['mirror_all']} | excluded={rep['excluded_by_filter']}")
    print(f"[SAVED] data/engine/mirror-backtest-{day}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
