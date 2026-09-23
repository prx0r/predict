"""bneck prices — $0 live pricing: 5-min cache first, Yahoo-live fallback.

Yahoo v8 chart (stocks/ETFs) + CoinGecko simple/price (crypto), keyless.
Cache: data/prices_latest.json written by scripts/poll.py (fresh <= 20 min).
Never raises; missing tickers are simply absent. Stdlib only.
"""
from __future__ import annotations

import datetime
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "prices_latest.json"
CACHE_MAX_AGE_S = 20 * 60

YAHOO_MAP = {
    "IONQ": "IONQ", "RGTI": "RGTI", "QBTS": "QBTS", "QNT": "QNT",
    "GFS": "GFS", "FORM": "FORM", "KEYS": "KEYS", "COHR": "COHR", "LITE": "LITE",
    "CEVA": "CEVA", "POWI": "POWI", "SYNA": "SYNA", "SLAB": "SLAB",
    "NVDA": "NVDA", "ARM": "ARM", "LSCC": "LSCC",
    "LPK": "LPK.DE", "SMHN": "SMHN.DE", "SOI": "SOI.PA",
    "ALNT": "ALNT", "TKR": "TKR", "NOVT": "NOVT", "MU": "MU", "DRAM": "DRAM",
}
CRYPTO_IDS = {
    "ETH": "ethereum",
    "QRL": "quantum-resistant-ledger",
    "QANX": "qanplatform",
    "CELL": "cellframe",
    "MINIMA": "minima",
}

UA = {"User-Agent": "Mozilla/5.0 (bneck-poller)"}


def _fetch_json(url: str, timeout: int = 20) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def poll_stock(ticker: str) -> dict:
    symbol = YAHOO_MAP.get(ticker, ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=5m&range=1d"
    body = _fetch_json(url) or {}
    try:
        meta = body.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        if price is None:
            return {"ticker": ticker, "error": "no price"}
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        pct = meta.get("regularMarketChangePercent")
        if pct is None and prev:
            pct = (price - prev) / prev * 100 if prev else 0
        asof = (datetime.datetime.fromtimestamp(meta["regularMarketTime"], tz=datetime.timezone.utc).isoformat()
                if meta.get("regularMarketTime") else None)
        return {"ticker": ticker, "price": round(float(price), 2),
                "pct_1d": round(float(pct or 0), 3), "prev_close": prev,
                "day_high": meta.get("regularMarketDayHigh"),
                "day_low": meta.get("regularMarketDayLow"),
                "volume": meta.get("regularMarketVolume"),
                "asof": asof, "venue": "yahoo"}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)[:120]}


def history(ticker: str, range_: str = "1mo") -> dict:
    """Daily closes via Yahoo v8 chart (keyless). Returns
    {ticker, closes: [{date, close}...]}. Never raises.
    Content-cached per (ticker, range, today) — free replays intraday."""
    import datetime as _dt
    from bneck2 import lab as _LAB
    ckey = _LAB.cache_key("yahoo", ticker, range_,
                          _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d"))
    hit = _LAB.cache_get(ckey)
    if isinstance(hit, dict) and hit.get("closes"):
        return hit
    symbol = YAHOO_MAP.get(ticker, ticker)
    if ticker in CRYPTO_IDS:
        return {"ticker": ticker, "closes": [], "error": "crypto history unsupported"}
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?interval=1d&range={urllib.parse.quote(range_)}")
    body = _fetch_json(url) or {}
    try:
        res = body.get("chart", {}).get("result", [{}])[0]
        ts = res.get("timestamp", [])
        closes = ((res.get("indicators", {}).get("quote", [{}])[0].get("close")) or [])
        out = [{"date": datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).strftime("%Y-%m-%d"),
                "close": round(float(c), 2)}
               for t, c in zip(ts, closes) if c is not None]
        res = {"ticker": ticker, "closes": out}
        _LAB.cache_set(ckey, res)
        return res
    except Exception as exc:
        return {"ticker": ticker, "closes": [], "error": str(exc)[:120]}


def crypto_history(coin: str = "bitcoin", days: int = 90) -> dict:
    """Daily closes via CoinGecko market_chart (keyless, cached per day)."""
    import datetime as _dt
    from bneck2 import lab as _LAB
    ckey = _LAB.cache_key("coingecko", coin, str(days),
                          _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d"))
    hit = _LAB.cache_get(ckey)
    if isinstance(hit, dict) and hit.get("closes"):
        return hit
    import urllib.parse as _up
    url = (f"https://api.coingecko.com/api/v3/coins/{_up.quote(coin)}/market_chart"
           f"?vs_currency=usd&days={int(days)}&interval=daily")
    body = _fetch_json(url, timeout=30) or {}
    out = []
    for ts_ms, px in body.get("prices", []) or []:
        try:
            out.append({"date": _dt.datetime.fromtimestamp(ts_ms / 1000, tz=_dt.timezone.utc).strftime("%Y-%m-%d"),
                        "close": round(float(px), 2)})
        except (ValueError, TypeError):
            continue
    res = {"ticker": coin.upper(), "closes": out}
    if out:
        _LAB.cache_set(ckey, res)
    return res


def forward_return(ticker: str, start: str, days: int = 5,
                   range_: str = "3mo") -> dict:
    """Close-to-close return over `days` trading days from `start` (YYYY-MM-DD)."""
    h = history(ticker, range_)
    closes = h.get("closes", [])
    idx = next((i for i, r in enumerate(closes) if r["date"] >= start), None)
    if idx is None or idx + days >= len(closes):
        return {"ticker": ticker, "start": start, "return": None,
                "note": "insufficient history"}
    a, b = closes[idx]["close"], closes[idx + days]["close"]
    return {"ticker": ticker, "start": closes[idx]["date"],
            "end": closes[idx + days]["date"],
            "return": round((b - a) / a, 4) if a else None}


def poll_crypto() -> dict[str, dict]:
    ids = ",".join(CRYPTO_IDS.values())
    url = ("https://api.coingecko.com/api/v3/simple/price"
           f"?ids={urllib.parse.quote(ids)}&vs_currencies=usd&include_24hr_change=true")
    body = _fetch_json(url) or {}
    out = {}
    for ticker, cid in CRYPTO_IDS.items():
        row = body.get(cid) or {}
        if "usd" not in row:
            out[ticker] = {"ticker": ticker, "error": "no data", "venue": "coingecko"}
        else:
            out[ticker] = {"ticker": ticker, "price": row["usd"],
                           "pct_1d": round(float(row.get("usd_24h_change") or 0), 3),
                           "venue": "coingecko"}
    return out


def snapshot() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tickers = {t: poll_stock(t) for t in YAHOO_MAP}
    tickers.update(poll_crypto())
    return {"ts": now, "cost": "$0 (yahoo+coingecko, keyless)", "tickers": tickers}


def get_moves(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """Cache first, live fallback per missing ticker. Never raises."""
    wanted = [t.upper() for t in tickers]
    moves: dict[str, dict] = {}
    try:
        if CACHE.is_file() and time.time() - CACHE.stat().st_mtime <= CACHE_MAX_AGE_S:
            body = json.loads(CACHE.read_text(encoding="utf-8"))
            snap = body.get("tickers", {})
            for t in wanted:
                row = snap.get(t)
                if isinstance(row, dict) and "price" in row:
                    moves[t] = {"price": row["price"],
                                "pct_1d": round(float(row.get("pct_1d") or 0), 2),
                                "asof": row.get("asof") or body.get("ts"),
                                "venue": row.get("venue", "cache-5m")}
    except Exception:
        pass
    for t in [x for x in wanted if x not in moves]:
        try:
            if t in CRYPTO_IDS:
                row = poll_crypto().get(t, {})
            else:
                row = poll_stock(t)
            if "price" in row:
                moves[t] = {"price": row["price"],
                            "pct_1d": round(float(row.get("pct_1d") or 0), 2),
                            "asof": row.get("asof", "yahoo-live"),
                            "venue": row.get("venue", "yahoo-live")}
        except Exception:
            continue
    return moves
