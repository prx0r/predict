"""Manifold Markets collector — third pm-club venue, keyless reads ($0).

api.manifold.markets: /v0/search-markets (public GETs). Adds a third
belief distribution beside Polymarket/Kalshi for triangulation (goated
§35: disagreement BETWEEN markets may itself be alpha).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://api.manifold.markets/v0"


def search_url(term: str, limit: int = 20) -> str:
    return f"{API}/search-markets?{urllib.parse.urlencode({'term': term, 'limit': limit})}"


def parse_markets(doc: list) -> list[dict]:
    out = []
    for m in doc if isinstance(doc, list) else []:
        try:
            p = float(m.get("probability", 0))
        except (ValueError, TypeError):
            p = 0.0
        out.append({"question": str(m.get("question", ""))[:160],
                    "p": round(p, 3),
                    "volume": float(m.get("volume", 0) or 0),
                    "liquidity": float(m.get("pool", {}).get("NO", 0) or 0)
                    + float(m.get("pool", {}).get("YES", 0) or 0),
                    "venue": "manifold",
                    "url": m.get("url", "") or ""})
    return out


def fetch_markets(term: str, limit: int = 20, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(search_url(term, limit),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        rows = parse_markets(doc)
        from collectors import polymarket as PM
        for x in rows:
            x["tier"] = PM.liquidity_tier(x["volume"], x["liquidity"])
        return rows
    except Exception:
        return []
