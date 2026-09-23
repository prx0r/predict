"""Polymarket whale tracker — read-only top-trader recipes, stdlib ($0).

Ports the working patterns from third_party/polytrack (zero-dep, live) and
third_party/polywhale (Data API map: /positions /trades /activity /value
/holders + CLOB /book /midpoint). Never places orders, holds no keys.

Entry points:
  top_holders(condition_id) -> per-outcome holder lists
  wallet_positions(wallet)  -> positions + lightweight stats
  consensus(markets)        -> N+ distinct wallets, same outcome (strongest
                               read-only signal polytrack tracks)
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

DATA = "https://data-api.polymarket.com"
UA = {"User-Agent": "bneck"}


def _get(path: str, params: dict) -> list | dict | None:
    try:
        url = f"{DATA}{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def top_holders(condition_id: str, limit: int = 20) -> list[dict]:
    """[{wallet, outcome, amount}] across both outcomes, size-desc."""
    doc = _get("/holders", {"market": condition_id, "limit": limit})
    out = []
    for leg in doc or []:
        try:
            outcome = int(leg.get("outcomeIndex", 0))
        except (ValueError, TypeError):
            outcome = 0
        for h in leg.get("holders", []) or []:
            try:
                amt = float(h.get("amount", 0))
            except (ValueError, TypeError):
                continue
            out.append({"wallet": h.get("proxyWallet", ""),
                        "outcome": outcome, "amount": amt,
                        "name": h.get("pseudonym") or h.get("name", "")})
    out.sort(key=lambda r: -r["amount"])
    return out


def wallet_positions(wallet: str, limit: int = 50) -> dict:
    """Positions + stats: n, total value, avg %PnL, winners rate."""
    rows = _get("/positions", {"user": wallet, "limit": limit,
                               "sortBy": "CURRENT", "sortDirection": "DESC"}) or []
    n = len(rows)
    tot = sum(float(r.get("currentValue", 0) or 0) for r in rows)
    pnls = [float(r.get("percentPnl", 0) or 0) for r in rows]
    wins = sum(1 for p in pnls if p > 0)
    return {"wallet": wallet, "n": n, "total_value": round(tot, 2),
            "avg_pct_pnl": round(sum(pnls) / n, 4) if n else 0.0,
            "win_rate": round(wins / n, 3) if n else 0.0}


def wallet_trades(wallet: str, limit: int = 50) -> list[dict]:
    rows = _get("/trades", {"user": wallet, "limit": limit}) or []
    return rows if isinstance(rows, list) else []


def consensus(markets: list[dict], min_wallets: int = 3,
              min_usd: float = 1000.0,
              holders_fn=None) -> list[dict]:
    """N+ distinct wallets on the same outcome of one market.

    markets: [{question, conditionId, p, ...}]. Returns ranked
    [{question, conditionId, outcome, wallets, total_usd}]."""
    fetch = holders_fn or top_holders
    out = []
    for m in markets:
        cid = m.get("conditionId") or ""
        if not cid:
            continue
        by_outcome: dict[int, dict[str, float]] = {}
        for h in fetch(cid):
            if h["amount"] < min_usd or not h["wallet"]:
                continue
            leg = by_outcome.setdefault(h["outcome"], {})
            leg[h["wallet"]] = leg.get(h["wallet"], 0.0) + h["amount"]
        for outcome, wallets in by_outcome.items():
            if len(wallets) >= min_wallets:
                out.append({"question": (m.get("question") or "")[:160],
                            "conditionId": cid, "outcome": outcome,
                            "wallets": sorted(wallets, key=lambda w: -wallets[w]),
                            "n_wallets": len(wallets),
                            "total_usd": round(sum(wallets.values()), 2)})
    out.sort(key=lambda r: -r["total_usd"])
    return out
