"""FX collector — currency context, keyless ($0).

Frankfurter (ECB reference rates, no key). USD/EUR/JPY triangles for
macro backdrop (risk-on/off, yen-carry stress reads). Recipe
ex-third_party/finance-mcp2.
"""
from __future__ import annotations

import json
import urllib.request

UA = {"User-Agent": "bneck"}
BASE = "https://api.frankfurter.dev/v1"


def _get(url: str, timeout: int = 20):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def latest(base: str = "USD", symbols: str = "EUR,JPY,GBP,CHF") -> dict:
    doc = _get(f"{BASE}/latest?base={base}&symbols={symbols}") or {}
    return {"date": doc.get("date", ""), "base": base,
            "rates": doc.get("rates", {})}


def series(pair_from: str = "USD", pair_to: str = "JPY",
           start: str = "2026-01-01", end: str = "2026-09-10") -> list[dict]:
    doc = _get(f"{BASE}/{start}..{end}?base={pair_from}&symbols={pair_to}") or {}
    rates = doc.get("rates", {})
    return [{"date": d, "rate": (v or {}).get(pair_to)}
            for d, v in sorted(rates.items()) if (v or {}).get(pair_to)]
