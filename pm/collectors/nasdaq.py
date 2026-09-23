"""Nasdaq Data Link collectors — institutional holders + insider aggregates.

api.nasdaq.com (keyless with browser UA): 13F-derived holder tables
(owner, shares, change, value) + insider buy/sell counts. Works around
blocked SEC bulk hosts. Never raises.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
      "Accept": "application/json"}


def _get(url: str, timeout: int = 25):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def holders(ticker: str, limit: int = 25) -> dict:
    """Top institutional holders with share changes + ownership summary."""
    doc = _get("https://api.nasdaq.com/api/company/"
               f"{urllib.parse.quote(ticker)}/institutional-holdings"
               f"?limit={int(limit)}") or {}
    data = doc.get("data", {})
    summ = data.get("ownershipSummary", {})
    table = (data.get("holdingsTransactions", {}).get("table") or {})
    rows = table.get("rows", []) or []
    out = []
    for r in rows:
        try:
            chg = float(str(r.get("sharesChangePCT", "0")).replace("%", ""))
        except ValueError:
            chg = 0.0
        out.append({"owner": r.get("ownerName", "")[:50],
                    "shares": r.get("sharesHeld", ""),
                    "change_pct": chg,
                    "value": r.get("marketValue", "")})
    get = lambda *ks: next((summ.get(k, {}).get("value") for k in ks
                            if isinstance(summ.get(k), dict)), "")
    return {"ticker": ticker.upper(),
            "inst_pct": get("SharesOutstandingPCT"),
            "total_value": get("TotalHoldingsValue"),
            "holders": out,
            "total_records": (data.get("holdingsTransactions") or {}).get("totalRecords", 0)}


def accumulators(holders_rows: list[dict], min_pct: float = 2.0) -> list[dict]:
    """Holders adding >= min_pct: institutional accumulation leg."""
    return [h for h in holders_rows if h.get("change_pct", 0) >= min_pct]


def insider_counts(ticker: str) -> dict:
    """Open-market buys vs sells counts (3m/12m)."""
    doc = _get("https://api.nasdaq.com/api/company/"
               f"{urllib.parse.quote(ticker)}/insider-trades?limit=5") or {}
    rows = ((doc.get("data") or {}).get("numberOfTrades") or {}).get("rows", []) or []
    out = {}
    for r in rows:
        out[r.get("insiderTrade", "?")] = {"m3": r.get("months3"),
                                           "m12": r.get("months12")}
    return {"ticker": ticker.upper(), "counts": out}
