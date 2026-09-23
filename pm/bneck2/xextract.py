"""X equities extractor — direction + tickers + levels, evidence spans.

Port of BEAR extractor_v2 discipline: regex, no asset defaults (UNKNOWN),
evidence spans quoted per claim. Tickers = NVDA universe + $cashtags.
"""
from __future__ import annotations

import re

LONG_KW = ["long", "buy", "bullish", "accumulate", "breakout", "beat",
           "raises", "raise", "growth", "record", "surge"]
SHORT_KW = ["short", "sell", "bearish", "miss", "cut", "downgrade", "slump",
            "plunge", "warning"]
LEVEL_KW = ["support", "resistance", "target", "price target", "tp", "sl",
            "stop", "entry", "exit"]

TICKERS = ["NVDA", "NVIDIA", "AMD", "AVGO", "BROADCOM", "MU", "MICRON",
           "TSM", "TSMC", "INTC", "MSFT", "GOOGL", "AMZN", "META", "ARM",
           "LRCX", "AMAT", "KLAC", "MRVL", "ANET", "CIEN", "LITE", "COHR",
           "FORM", "ONTO", "HBM", "BLACKWELL", "RUBIN", "COWOS", "CPO"]


def classify(text: str) -> dict:
    lower = (text or "").lower()
    has_long = any(re.search(r"\b" + k + r"\b", lower) for k in LONG_KW)
    has_short = any(re.search(r"\b" + k + r"\b", lower) for k in SHORT_KW)
    ticks = sorted({t for t in TICKERS
                    if re.search(r"\$" + t + r"\b|\b" + t + r"\b", text.upper())})
    levels = []
    for m in re.finditer(r"\$ ?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", text):
        try:
            v = float(m.group(1).replace(",", ""))
            if 5 < v < 5000:
                levels.append(v)
        except ValueError:
            continue
    if has_long and not has_short:
        direction, kind = "LONG", "DIRECTIONAL"
    elif has_short and not has_long:
        direction, kind = "SHORT", "DIRECTIONAL"
    elif any(re.search(r"\b" + k + r"\b", lower) for k in LEVEL_KW):
        direction, kind = None, "LEVELS"
    else:
        direction, kind = None, "COMMENTARY"
    return {"direction": direction, "kind": kind,
            "tickers": ticks if ticks else ["UNKNOWN"],
            "levels": levels[:5]}


def _ts(t: dict) -> str:
    from datetime import datetime
    raw = t.get("createdAt") or t.get("created_at") or t.get("date") or ""
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:31], fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return str(raw)[:10]


def density(tweets: list[dict]) -> dict:
    """BEAR gate: (directional + levels) / standalone, ex-replies/media."""
    standalone = [t for t in tweets
                  if not t.get("isReply", t.get("is_reply"))
                  and not t.get("has_media") and not t.get("media")]
    if not standalone:
        return {"density": 0.0, "n": 0}
    scored = sum(1 for t in standalone
                 if classify(str(t.get("text", t.get("full_text", ""))))["kind"]
                 in ("DIRECTIONAL", "LEVELS"))
    return {"density": round(scored / len(standalone), 3), "n": len(standalone)}
