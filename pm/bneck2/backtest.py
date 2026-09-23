"""bneck2 backtest — leakage-safe walk-forward, stdlib port of the vendored
postagi_kernel/backtest.py (which needs numpy/pandas).

Protocol (peer-review P0 fix: explicit calendar clock):
  each row = {date (decision/asof), ticker, score, forward_return,
              entry_date, exit_date, horizon_days}.
  forward_return spans entry_date -> exit_date where entry is the first
  trading day AFTER date (next-candle, no same-day peeking).
  Annualization derives from elapsed calendar days, never a hard-coded 12.
  Dates spaced closer than horizon_days = overlapping vintages: flagged
  OVERLAPPING and Sharpe is labelled provisional (compounding overlapping
  forwards as independent periods has no stable interpretation).
  Turnover-charged costs; no same-period look-ahead.

Live panel accumulation (data/backtest/panel.jsonl): oneclick appends
score snapshots per pass; forward returns fill in once closes exist;
walk_forward runs only on complete dates. Until then: INSUFFICIENT.
"""
from __future__ import annotations

import json
import math
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "backtest" / "panel.jsonl"


def make_positions(scores: dict[str, float], quantile: float = 0.2,
                   gross: float = 1.0) -> dict[str, float]:
    if not 0 < quantile < 0.5:
        raise ValueError("quantile must be in (0,.5)")
    order = sorted(scores, key=lambda t: scores[t])
    n = max(1, int(len(order) * quantile))
    pos = {t: 0.0 for t in order}
    for t in order[:n]:
        pos[t] = -gross / (2 * n)
    for t in order[-n:]:
        pos[t] = gross / (2 * n)
    return pos


def _d(s: str) -> _date:
    s = str(s)[:10]
    try:
        return _date.fromisoformat(s)
    except ValueError:
        pass
    m = __import__("re").match(r"^(\d{4})-(\d{2})$", s)
    if m:
        return _date(int(m.group(1)), int(m.group(2)), 1)
    raise ValueError(f"walk_forward dates must be YYYY-MM-DD (got {s!r})")


def walk_forward(panel: list[dict], cost_bps: float = 10.0,
                 quantile: float = 0.2,
                 horizon_days: int = 5) -> tuple[list[dict], dict]:
    dates: dict[str, list[dict]] = {}
    for r in panel:
        dates.setdefault(str(r["date"]), []).append(r)
    ordered = sorted(dates)
    prev: dict[str, float] = {}
    rows = []
    for date in ordered:
        g = dates[date]
        pos = make_positions({r["ticker"]: float(r["score"]) for r in g},
                             quantile)
        ret = {r["ticker"]: float(r["forward_return"]) for r in g}
        tickers = set(pos) | set(prev)
        turnover = sum(abs(pos.get(t, 0.0) - prev.get(t, 0.0))
                       for t in tickers)
        gross = sum(pos[t] * ret.get(t, 0.0) for t in pos)
        cost = turnover * cost_bps / 10000
        rows.append({"date": date, "gross_return": round(gross, 6),
                     "turnover": round(turnover, 6), "cost": round(cost, 6),
                     "net_return": round(gross - cost, 6)})
        prev = pos
    nets = [r["net_return"] for r in rows]
    n = len(nets)
    # Calendar clock: annualize from elapsed days, not a hard-coded 12.
    span_days = max((_d(ordered[-1]) - _d(ordered[0])).days, horizon_days) if n else horizon_days
    years = span_days / 365.25
    ppy = n / years if years > 0 else 0.0  # effective observations per year
    # Overlap: rebalance steps closer than the holding horizon compound
    # overlapping forwards as if independent — flag, don't hide.
    steps = [(_d(ordered[i + 1]) - _d(ordered[i])).days for i in range(n - 1)]
    overlapping = bool(steps) and (sum(steps) / len(steps) < horizon_days)
    ann = ((math.prod(1 + x for x in nets)) ** (1.0 / years) - 1) if n and years > 0 else 0.0
    mean = sum(nets) / n if n else 0.0
    var = sum((x - mean) ** 2 for x in nets) / (n - 1) if n > 1 else 0.0
    vol = math.sqrt(var) * math.sqrt(ppy) if n > 1 and ppy > 0 else 0.0
    cum, peak, max_dd = 1.0, 1.0, 0.0
    for x in nets:
        cum *= 1 + x
        peak = max(peak, cum)
        max_dd = min(max_dd, cum / peak - 1)
    stats: dict = {"annualized_return": round(ann, 6),
                   "annualized_vol": round(vol, 6),
                   "sharpe": round(ann / vol, 4) if vol > 0 else 0.0,
                   "max_drawdown": round(max_dd, 6), "periods": n,
                   "cost_bps": cost_bps, "horizon_days": horizon_days,
                   "span_days": span_days,
                   "overlapping": overlapping}
    if overlapping:
        stats["sharpe_note"] = ("provisional-overlap: rebalance step < "
                                "horizon; compounded forwards overlap")
    return rows, stats


def load_panel(path: Path = PANEL_PATH) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []


def append_snapshot(date: str, scores: dict[str, float],
                    path: Path = PANEL_PATH) -> int:
    """One score row per ticker. Skips dates already present (idempotent)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    have = {(r.get("date"), r.get("ticker")) for r in load_panel(path)}
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for t, s in sorted(scores.items()):
            if (date, t) not in have:
                f.write(json.dumps({"date": date, "ticker": t, "score": s,
                                    "forward_return": None}) + "\n")
                n += 1
    return n


def fill_forwards(path: Path = PANEL_PATH, days: int = 5) -> int:
    """Fill forward_return where closes now exist. Returns filled count.

    Entry = first trading day AFTER `date` (next-candle: a signal known at
    `date` cannot trade `date`'s close). Exit = entry + `days` trading days.
    Rows record entry_date/exit_date/horizon_days/clock so the convention
    is auditable per row. Legacy rows (no entry_date) keep their
    date-based forwards untouched.
    """
    from bneck2 import prices as P
    rows = load_panel(path)
    if not rows:
        return 0
    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r)
    filled = 0
    for t, rs in by_ticker.items():
        hist = {c["date"]: c["close"] for c in P.history(t).get("closes", [])}
        dates = sorted(hist)
        for r in rs:
            if r.get("forward_return") is not None or r["date"] not in hist:
                continue
            i = dates.index(r["date"])
            entry = i + 1
            if entry + days >= len(dates) or not hist[dates[entry]]:
                continue
            r["forward_return"] = round(
                (hist[dates[entry + days]] - hist[dates[entry]]) / hist[dates[entry]], 4)
            r["entry_date"] = dates[entry]
            r["exit_date"] = dates[entry + days]
            r["horizon_days"] = days
            r["clock"] = "next-close"
            filled += 1
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")
    return filled


def live_result(path: Path = PANEL_PATH) -> dict:
    """walk_forward on complete dates, else INSUFFICIENT (never faked)."""
    rows = [r for r in load_panel(path) if r.get("forward_return") is not None]
    dates = sorted({r["date"] for r in rows})
    if len(dates) < 2:
        return {"status": "INSUFFICIENT",
                "complete_dates": len(dates),
                "need": ">=2 complete 5d-forward dates"}
    _, stats = walk_forward(rows)
    if stats.get("max_drawdown", 0) is not None and stats["max_drawdown"] <= -0.5:
        return {"status": "BLOCKED", **stats,
                "note": "drawdown gate: review machinery, not a result"}
    return {"status": "OK", **stats}
