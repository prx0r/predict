"""bneck2 leads — lead-lag math across datastreams (who comes first?).

For two weekly series X (candidate leader) and Y (target), report Pearson r
at lags -4..+4 weeks. Positive lag k means X shifted back k weeks still
correlates with Y now => X LEADS Y by k. Peak lag + peak r + n reported;
n<8 => directional-only. All inputs timestamped; no peeking (series built
from records dated <= window end).
"""
from __future__ import annotations

import math


def weekly_buckets(dates: list[str], start: str, weeks: int) -> list[str]:
    import datetime as _dt
    y, m, d = map(int, start.split("-"))
    base = _dt.date(y, m, d)
    return [(base + _dt.timedelta(weeks=k)).isoformat() for k in range(weeks)]


def bucketize(events: list[str], starts: list[str]) -> list[int]:
    """Count events per [start[i], start[i+1]) week."""
    out = [0] * len(starts)
    for e in events:
        for i in range(len(starts) - 1, -1, -1):
            if e >= starts[i]:
                out[i] += 1
                break
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs)
    vx = sum((a - mx) ** 2 for a, _ in pairs)
    vy = sum((b - my) ** 2 for _, b in pairs)
    if not vx or not vy:
        return None
    return round(cov / math.sqrt(vx * vy), 3)


def xcorr(x: list[float], y: list[float],
          max_lag: int = 4) -> list[dict]:
    """r(k) for k in -max..+max. k>0: X leads Y by k (X back-shifted)."""
    out = []
    n = len(x)
    for k in range(-max_lag, max_lag + 1):
        if k >= 0:
            xs, ys = x[:n - k], y[k:]
        else:
            xs, ys = x[-k:], y[:n + k]
        r = pearson(xs, ys)
        out.append({"lag": k, "r": r, "n": len(xs)})
    return out


def lead_lag(x: list[float], y: list[float], max_lag: int = 4) -> dict:
    rows = [r for r in xcorr(x, y, max_lag) if r["r"] is not None]
    if not rows:
        return {"peak_lag": None, "peak_r": None, "n": 0,
                "verdict": "INSUFFICIENT"}
    best = max(rows, key=lambda r: abs(r["r"]))
    side = "X-leads" if best["lag"] > 0 else "Y-leads" if best["lag"] < 0 else "sync"
    return {"peak_lag": best["lag"], "peak_r": best["r"], "n": best["n"],
            "curve": [(r["lag"], r["r"]) for r in rows],
            "verdict": f"{side}@{abs(best['lag'])}w r={best['r']}"}
