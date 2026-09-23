"""Polymarket collector — probability clock with market-quality context ($0).

Signal is (p, volume, liquidity, spread, velocity), never p alone:
high-liquidity reads ~0.82 reliability, thin books ~coin-flip (calibration
priors in bneck/calibration.py). Gamma search API, no key.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"


def search_url(query: str, limit: int = 10) -> str:
    return f"{GAMMA}/public-search?{urllib.parse.urlencode({'q': query, 'limit_tag': limit})}"


def parse_markets(doc: list | dict) -> list[dict]:
    events = doc if isinstance(doc, list) else doc.get("events", [])
    out = []
    for ev in events if isinstance(events, list) else []:
        for m in ev.get("markets", [ev]):
            try:
                prices = json.loads(m.get("outcomePrices") or "[]")
                p = round(float(prices[0]), 3) if prices else 0.0
            except (ValueError, TypeError):
                p = 0.0
            try:
                vol = float(m.get("volume") or ev.get("volume") or 0)
                liq = float(m.get("liquidity") or 0)
            except (ValueError, TypeError):
                vol, liq = 0.0, 0.0
            out.append({"question": (m.get("question") or ev.get("title", ""))[:160],
                        "p": p, "volume": vol, "liquidity": liq,
                        "conditionId": m.get("conditionId") or ""})
    return out


def liquidity_tier(volume: float, liquidity: float) -> str:
    if volume >= 2_000_000 or liquidity >= 200_000:
        return "high-liquidity"
    if volume >= 100_000 or liquidity >= 10_000:
        return "mid-liquidity"
    return "low-liquidity"


def fetch_markets(query: str, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(search_url(query),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        rows = parse_markets(doc)
        for m in rows:
            m["tier"] = liquidity_tier(m["volume"], m["liquidity"])
        return rows
    except Exception:
        return []
