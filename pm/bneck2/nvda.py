"""NVDA alpha harness — beat buy-hold with alt signals, ≤3x gross.

Daily grid, point-in-time features only, next-day execution, 5bps/unit
turnover cost. Train/test split by date. Bogeys: buy-hold 1x, buy-hold
3x (the real bogey at 3x cap), SPY.
"""
from __future__ import annotations

import math

CAP = 3.0
COST = 0.0005


def features(dates: list[str], closes: dict[str, float],
             sec_by_date: dict[str, dict],
             short_by_date: dict[str, float],
             hn_by_date: dict[str, int]) -> dict[str, dict]:
    out = {}
    cl = sorted(closes)
    for i, d in enumerate(dates):
        if d not in closes:
            continue
        m20 = None
        past = [x for x in cl if x <= d]
        if len(past) > 20 and past[-21] and closes[past[-21]]:
            m20 = (closes[past[-1]] - closes[past[-21]]) / closes[past[-21]]
        s = sec_by_date.get(d, {})
        out[d] = {"mom_20": m20,
                  "burst": s.get("burst", 0.0),
                  "short": short_by_date.get(d),
                  "hn": hn_by_date.get(d, 0)}
    return out


def size_rule(feats: dict, mode: str) -> float:
    """Exposure in [-1, +3] (modes decide direction)."""
    if mode == "mom":
        m = feats.get("mom_20") or 0.0
        return max(-1.0, min(3.0, 12.0 * m))
    if mode == "burst_fade":
        # bursts mark tops (E018/E021): cut exposure after bursts
        b = feats.get("burst", 0.0)
        return max(0.0, 3.0 - b)
    if mode == "short_fade":
        s = feats.get("short")
        if s is None:
            return 1.0
        return max(0.0, min(3.0, 3.0 * (0.6 - s) / 0.6))
    if mode == "combo":
        parts = []
        m = feats.get("mom_20")
        if m is not None:
            parts.append(max(-1.0, min(1.0, 12.0 * m)))
        s = feats.get("short")
        if s is not None:
            parts.append(max(-1.0, min(1.0, (0.5 - s) / 0.5)))
        b = feats.get("burst", 0.0)
        parts.append(-min(b / 3.0, 1.0))
        return max(-1.0, min(3.0, 3.0 * sum(parts) / max(len(parts), 1)))
    if mode == "buyhold3x":
        return 3.0
    return 1.0  # buyhold1x


def run(dates: list[str], closes: dict[str, float],
        feats: dict[str, dict], mode: str) -> dict:
    """Next-day execution: exposure set at close t earns t->t+1."""
    eq, prev, peak, maxdd = 1.0, 0.0, 1.0, 0.0
    rets = []
    cl = sorted(d for d in closes)
    for i, d in enumerate(dates):
        if d not in closes:
            continue
        j = cl.index(d)
        if j + 1 >= len(cl):
            continue
        r = (cl[j + 1] and closes[d] and
             (closes[cl[j + 1]] - closes[d]) / closes[d]) or 0.0
        w = size_rule(feats.get(d, {}), mode)
        turnover = abs(w - prev)
        net = w * r - turnover * COST
        eq *= 1 + net
        rets.append(net)
        peak = max(peak, eq)
        maxdd = min(maxdd, eq / peak - 1)
        prev = w
    n = len(rets)
    yrs = n / 252 if n else 0
    ann = eq ** (1 / yrs) - 1 if yrs > 0 else 0.0
    mu = sum(rets) / n if n else 0.0
    var = sum((x - mu) ** 2 for x in rets) / (n - 1) if n > 1 else 0.0
    vol = math.sqrt(var * 252) if n > 1 else 0.0
    return {"total": round(eq - 1, 4), "ann": round(ann, 4),
            "sharpe": round(ann / vol, 3) if vol > 0 else 0.0,
            "maxdd": round(maxdd, 4), "n": n}
