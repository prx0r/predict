"""bneck2 acq — acquisition-chain event study (HEP mutate-and-rerun).

Tests whether frontier-lab capital events move counterparty prices:
for each dated commitment with a public counterparty ticker, 20-trading-day
forward return vs SPY from the event date (Yahoo daily closes, keyless).

Counterparty map is explicit and auditable; ambiguous/private targets are
DROPPED (listed in dropped()), never proxied. Small-n: directional only.
"""
from __future__ import annotations

# (lab, target-substring) -> tickers. Order matters: first match wins.
COUNTERPARTY_MAP: list[tuple[str, str, list[str]]] = [
    ("OpenAI", "AMD", ["AMD"]),
    ("xAI", "NVIDIA/Cisco", ["NVDA", "CSCO"]),
    ("OpenAI", "SB Energy", ["9984.T"]),
    ("OpenAI", "Amazon/NVIDIA/SoftBank", ["AMZN", "NVDA", "9984.T"]),
    ("OpenAI", "Amazon/AWS Trainium", ["AMZN"]),
    ("Anthropic", "Google/Broadcom", ["GOOGL", "AVGO"]),
    ("Anthropic", "CoreWeave", ["CRWV"]),
    ("Meta", "Scale AI", ["META"]),
    ("OpenAI", "Broadcom", ["AVGO"]),
    ("Google", "Finland", ["GOOGL", "FORTUM.HE"]),
    ("OpenAI", "Samsung/SK Hynix", ["005930.KS", "000660.KS"]),
]

MARKET = "SPY"


def map_tickers(lab: str, target: str) -> list[str]:
    for l, sub, ticks in COUNTERPARTY_MAP:
        if l == lab and sub.lower() in (target or "").lower():
            return ticks
    return []


def eligible(commitments: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split into (testable, dropped). Drops: placeholder dates, private/
    ambiguous targets. Dropped rows are returned with reasons (audit)."""
    good, dropped = [], []
    for c in commitments:
        d = c.get("date", "")
        if len(d) != 10 or d in ("2026-01-01",):
            dropped.append({**c, "reason": "placeholder-date"})
            continue
        ticks = map_tickers(c.get("lab", ""), c.get("target", ""))
        if not ticks:
            dropped.append({**c, "reason": "private-or-ambiguous-target"})
            continue
        good.append({**c, "tickers": ticks})
    return good, dropped


def event_study(commitments: list[dict], days: int = 20) -> list[dict]:
    """Forward return per (event, ticker) vs SPY. Needs Yahoo history."""
    from bneck2 import prices as P
    out = []
    mkt = {c["date"]: c["close"]
           for c in P.history(MARKET, "2y").get("closes", [])}
    mdates = sorted(mkt)
    for c in commitments:
        for t in c["tickers"]:
            hist = {x["date"]: x["close"]
                    for x in P.history(t, "2y").get("closes", [])}
            dates = sorted(hist)
            i = next((k for k, d in enumerate(dates) if d >= c["date"]), None)
            mi = next((k for k, d in enumerate(mdates) if d >= c["date"]), None)
            if i is None or mi is None or i + days >= len(dates) \
                    or mi + days >= len(mdates):
                out.append({"event": c["date"], "lab": c.get("lab"),
                            "target": c.get("target"), "ticker": t,
                            "kind": c.get("kind"), "excess": None,
                            "note": "insufficient forward history"})
                continue
            r = (hist[dates[i + days]] - hist[dates[i]]) / hist[dates[i]]
            m = (mkt[mdates[mi + days]] - mkt[mdates[mi]]) / mkt[mdates[mi]]
            out.append({"event": c["date"], "lab": c.get("lab"),
                        "target": (c.get("target") or "")[:50], "ticker": t,
                        "kind": c.get("kind"), "fwd": round(r, 4),
                        "spy": round(m, 4), "excess": round(r - m, 4)})
    return out


def summarize(rows: list[dict]) -> dict:
    xs = [r["excess"] for r in rows if r.get("excess") is not None]
    if not xs:
        return {"n": 0, "verdict": "INCONCLUSIVE"}
    pos = sum(1 for x in xs if x > 0.05)
    return {"n": len(xs), "mean_excess": round(sum(xs) / len(xs), 4),
            "hit_rate": round(pos / len(xs), 3),
            "verdict": ("CONFIRMED" if pos / len(xs) >= 0.6 and len(xs) >= 5
                        else "REFUTED" if len(xs) >= 5 else "INCONCLUSIVE")}
