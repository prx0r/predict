"""Kalshi collector — second pm-clock venue ($0, keyless).

Public market-data endpoints need no key:
  https://api.elections.kalshi.com/trade-api/v2
No full-text search param exists, so we page open events
(with_nested_markets=true) and keyword-match titles client-side.
Rows match the polymarket shape + venue tag so killfeed can take the
best book across venues. Volumes are contracts; liquidity_dollars is USD.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "bneck"}
MAX_PAGES = 3


def events_url(cursor: str = "", limit: int = 200) -> str:
    q = urllib.parse.urlencode({"status": "open",
                                "with_nested_markets": "true",
                                "limit": limit, "cursor": cursor})
    return f"{BASE}/events?{q}"


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (ValueError, TypeError):
        return default


def market_price(m: dict) -> float:
    """last trade, else mid of yes bid/ask (dollars are 0..1 VWAP-ish)."""
    last = _f(m.get("last_price_dollars"), -1.0)
    if last >= 0:
        return round(min(max(last, 0.0), 1.0), 3)
    bid, ask = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars"))
    if bid > 0 and ask > 0:
        return round(min(max((bid + ask) / 2, 0.0), 1.0), 3)
    return 0.0


def words(query: str) -> list[str]:
    return [w.lower() for w in query.replace("/", " ").split()
            if len(w) > 3]


def event_matches(ev: dict, keys: list[str]) -> bool:
    text = f"{ev.get('title', '')} {ev.get('sub_title', '')} "\
        f"{ev.get('category', '')} {ev.get('series_ticker', '')}".lower()
    return any(k in text for k in keys)


def parse_events(doc: dict, query: str) -> list[dict]:
    keys = words(query)
    out = []
    for ev in doc.get("events", []):
        if keys and not event_matches(ev, keys):
            continue
        title = str(ev.get("title", ""))[:160]
        for m in ev.get("markets", []) or []:
            out.append({"question": title, "p": market_price(m),
                        "series": ev.get("series_ticker", ""),
                        "ticker": m.get("ticker", ""),
                        "volume": _f(m.get("volume_24h_fp") or m.get("volume_fp")),
                        "liquidity": _f(m.get("liquidity_dollars")),
                        "venue": "kalshi"})
    return out


def fetch_markets(query: str, timeout: int = 30,
                  pages: int = MAX_PAGES) -> list[dict]:
    """All open-event pages (capped), filtered to query keywords."""
    from collectors import polymarket as PM
    out, cursor = [], ""
    try:
        for _ in range(max(1, pages)):
            req = urllib.request.Request(events_url(cursor),
                                         headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
            out.extend(parse_events(doc, query))
            cursor = doc.get("cursor", "")
            if not cursor:
                break
    except Exception:
        pass
    for m in out:
        m["tier"] = PM.liquidity_tier(m["volume"], m["liquidity"])
    return out


def candles_url(series_ticker: str, ticker: str, start_ts: int, end_ts: int,
                period: int = 1440) -> str:
    return (f"{BASE}/series/{series_ticker}/markets/{ticker}/candlesticks"
            f"?start_ts={int(start_ts)}&end_ts={int(end_ts)}"
            f"&period_interval={int(period)}")


def parse_candles(doc: dict) -> list[dict]:
    out = []
    for c in doc.get("candlesticks", []) or []:
        price = c.get("price") or {}
        try:
            close = float(price.get("close_dollars")) if price.get("close_dollars") is not None else None
        except (ValueError, TypeError):
            close = None
        out.append({"ts": c.get("end_period_ts"), "close": close,
                    "volume": float(c.get("volume_fp") or 0)})
    return out


def fetch_candles(series_ticker: str, ticker: str, start_ts: int, end_ts: int,
                  period: int = 1440, timeout: int = 30) -> list[dict]:
    """Daily OHLC price history per market (pm velocity input)."""
    try:
        req = urllib.request.Request(
            candles_url(series_ticker, ticker, start_ts, end_ts, period),
            headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_candles(json.loads(r.read().decode("utf-8", "replace")))
    except Exception:
        return []
