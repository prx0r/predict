"""CLOB depth collector — real orderbook depth for pm reads ($0, keyless).

Gamma gives indicative prices; CLOB /book gives bid/ask stacks per
clobTokenIds. Depth-weighted mid + spread tighten reliability beyond
the liquidity-tier heuristic (killfeed pm leg upgrade path).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://clob.polymarket.com"
UA = {"User-Agent": "bneck"}


def _get(path: str, params: dict, timeout: int = 20):
    try:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def book(token_id: str) -> dict:
    doc = _get("/book", {"token_id": token_id}) or {}
    bids = doc.get("bids", []) or []
    asks = doc.get("asks", []) or []
    def depth(levels, n=5):
        tot = 0.0
        for lvl in levels[:n]:
            try:
                tot += float(lvl.get("price", 0)) * float(lvl.get("size", 0))
            except (ValueError, TypeError):
                continue
        return round(tot, 2)
    bb = float((bids[0] or {}).get("price", 0) or 0) if bids else 0.0
    ba = float((asks[0] or {}).get("price", 0) or 0) if asks else 0.0
    mid = round((bb + ba) / 2, 4) if bb and ba else 0.0
    return {"bid": bb, "ask": ba, "mid": mid,
            "spread": round(ba - bb, 4) if bb and ba else None,
            "depth_top5": depth(bids) + depth(asks),
            "levels": len(bids) + len(asks)}
