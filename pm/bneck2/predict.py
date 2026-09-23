"""bneck2 predict — price-movement signal chain (targets first, then factors).

Panel: (date, ticker) rows over trailing-12-month monthly windows.
Features are STRICTLY point-in-time (nothing dated after the window):
  f_mom_20    20d trailing return (Yahoo, the bogey to beat)
  f_burst     SEC Form4+deal count trailing 30d vs trailing-1y median
  f_attack    OpenAlex prior-year growth for the node's query (lagged 1y)
  f_hn        HN stories trailing 90d (Algolia created_at_i ranges)
  f_short     FINRA short ratio, nearest tape before window
  f_conv      node conviction (static honesty-check: expect ~0 IC)
  f_B         node severity B (static honesty-check)
Target: 20-trading-day forward return (Yahoo).

Screen: Spearman IC + top-vs-bottom tercile hit-rate with Wilson bounds.
Composite: equal-weight z-scores of factors clearing IC>0.1 in TRAIN
(first 9 months); tested on HOLDOUT (last 3). Walk-forward via backtest.
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNIVERSE = ["NVDA", "AMD", "MU", "INTC", "FORM", "KEYS", "COHR", "LITE",
            "IONQ", "RGTI", "AVGO", "GOOGL", "AMZN", "META", "CSCO",
            "ONTO", "AEHR", "ALAB", "SNPS", "ANET", "MRVL", "ARM", "TSM",
            "CRWV", "NBIS", "NOK", "TER", "KLAC", "AMAT", "LRCX"]


def grid(freq: str = "monthly", n: int = 12) -> list[str]:
    """Rebalance dates. monthly: 12 month-ends. biweekly: 26 Fridays."""
    if freq == "biweekly":
        today = date.today()
        # most recent Friday
        fri = today - timedelta(days=(today.weekday() - 4) % 7)
        return [(fri - timedelta(weeks=2 * k)).isoformat()
                for k in range(2 * n - 1, -1, -1)]
    return month_ends(n)


def month_ends(n: int = 12) -> list[str]:
    today = date.today()
    first = today.replace(day=1)
    out = []
    for k in range(n, 0, -1):
        m = first.month - k
        y = first.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        last = (date(y + (m == 12), 1 if m == 12 else m + 1, 1)
                - timedelta(days=1))
        out.append(last.isoformat())
    return out


def _closes(ticker: str) -> list[tuple[str, float]]:
    from bneck2 import prices as P
    return [(c["date"], c["close"])
            for c in P.history(ticker, "2y").get("closes", [])]


def trailing_return(closes: list[tuple[str, float]], asof: str,
                    days: int) -> float | None:
    past = [(d, c) for d, c in closes if d <= asof]
    if len(past) < days + 1:
        return None
    a, b = past[-days - 1][1], past[-1][1]
    return round((b - a) / a, 4) if a else None


def forward_return(closes: list[tuple[str, float]], asof: str,
                   days: int = 20) -> float | None:
    idx = next((i for i, (d, _) in enumerate(closes) if d > asof), None)
    if idx is None or idx + days - 1 >= len(closes):
        return None
    a = closes[idx - 1][1] if idx > 0 else closes[idx][1]
    b = closes[idx + days - 1][1]
    return round((b - a) / a, 4) if a else None


_SUBMISSIONS_CACHE: dict[str, dict] = {}


def submissions(cik: str) -> dict:
    from collectors import sec as S
    if cik not in _SUBMISSIONS_CACHE:
        try:
            req = urllib.request.Request(
                S.submissions_url(cik),
                headers={"User-Agent": "bneck research contact@localhost",
                         "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                _SUBMISSIONS_CACHE[cik] = json.loads(
                    r.read().decode("utf-8", "replace"))
        except Exception:
            _SUBMISSIONS_CACHE[cik] = {}
    return _SUBMISSIONS_CACHE[cik]


def sec_counts_30d(cik: str, asof: str) -> dict:
    """Form4+deal counts in trailing 30d and trailing 1y (baseline)."""
    doc = submissions(cik)
    if not doc:
        return {"n30": None, "med": None}
    fl = (doc.get("filings") or {}).get("recent") or {}
    forms, dates = fl.get("form", []), fl.get("filingDate", [])
    n30 = yr = 0
    win, ywin = [], []
    for f, d in zip(forms, dates):
        if f not in ("4", "8-K", "13D", "13G") or not d:
            continue
        if d > asof:
            continue  # point-in-time: nothing after the window
        if d >= _shift(asof, -30):
            win.append(d)
        if d >= _shift(asof, -365):
            ywin.append(d)
    n30 = len(win)
    med = sorted([len([x for x in ywin if _shift(asof, -365 - 30 * k) <= x < _shift(asof, -30 * k)])
                  for k in range(12)])[6] if ywin else 0
    return {"n30": n30, "med": med,
            "burst": n30 >= 5 and n30 >= 2 * max(med, 1)}


def _shift(d: str, days: int) -> str:
    y, m, dd = map(int, d.split("-"))
    return (date(y, m, dd) + timedelta(days=days)).isoformat()


def hn_count_90d(query: str, asof: str) -> int | None:
    """HN stories in trailing 90d (Algolia numericFilters)."""
    try:
        lo = _shift(asof, -90)
        import calendar
        import datetime as _dt
        lo_ts = calendar.timegm(_dt.datetime.fromisoformat(lo).timetuple())
        hi_ts = calendar.timegm(_dt.datetime.fromisoformat(asof).timetuple())
        url = ("https://hn.algolia.com/api/v1/search?"
               + urllib.parse.urlencode(
                   {"query": query, "tags": "story",
                    "numericFilters": f"created_at_i>{lo_ts},created_at_i<{hi_ts}",
                    "hitsPerPage": 100}))
        req = urllib.request.Request(url, headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return int(json.loads(r.read().decode("utf-8", "replace")).get("nbHits", 0))
    except Exception:
        return None


def attack_lagged(node_query: str, asof_year: int) -> float | None:
    """Prior-year OpenAlex growth (lagged: research known at decision time)."""
    from collectors import openalex as OA
    vel = OA.fetch_yearly(node_query)
    if not vel.get("ok"):
        return None
    per = {int(k): v for k, v in vel.get("per_year", {}).items()
           if str(k).isdigit() and int(k) < asof_year}
    yrs = sorted(per)
    if len(yrs) < 4:
        return None
    recent = (per[yrs[-1]] + per[yrs[-2]]) / 2
    prior = (per[yrs[-3]] + per[yrs[-4]]) / 2
    return round(recent / prior - 1, 3) if prior else None


def build_panel(tickers: list[str] | None = None,
                months: int = 12, freq: str = "monthly") -> list[dict]:
    """Assemble the full panel (slow: network per ticker; cached where set)."""
    from bneck2 import graph as G
    from bneck2 import migration as M
    from bneck2 import quant as Q
    from bneck2 import killfeed as K
    tickers = tickers or UNIVERSE
    g = G.load_graph()
    readings = Q.load_readings()
    node_of: dict[str, dict] = {}
    for n in g["nodes"]:
        for t in n.get("tickers", []):
            node_of.setdefault(t, n)
    hist = {t: _closes(t) for t in tickers}
    dates = grid(freq, months)
    from collectors import finra as _FIN
    shorts = _FIN.short_history(
        [t for t in tickers if t.isupper() and len(t) <= 6], dates)
    rows = []
    for asof in dates:
        for t in tickers:
            cl = hist.get(t, [])
            if not cl:
                continue
            node = node_of.get(t, {})
            cik = K.CIK_MAP.get(t)
            sec = sec_counts_30d(cik, asof) if cik else {"n30": None, "med": None}
            q = K.node_queries(node).get("openalex", t) if node else t
            row = {
                "date": asof, "ticker": t,
                "f_mom_20": trailing_return(cl, asof, 20),
                "f_burst": (sec["n30"] / max(sec["med"] or 0, 1)
                            if sec["n30"] is not None else None),
                "f_attack": attack_lagged(q, int(asof[:4])),
                "f_hn": hn_count_90d(q.split("/")[0].strip(), asof),
                "f_short": shorts.get(asof, {}).get(t),
                "f_conv": G.score_node(node) if node else None,
                "f_B": M.severity(node, readings.get(node.get("id", "")))["B"] if node else None,
                "fwd_20": forward_return(cl, asof, 20),
            }
            rows.append(row)
            time.sleep(0.2)
    return rows


def spearman(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n < 5:
        return None
    rx = {v: i for i, v in enumerate(sorted(set(p[0] for p in pairs)))}
    ry = {v: i for i, v in enumerate(sorted(set(p[1] for p in pairs)))}
    dx = [rx[p[0]] for p in pairs]
    dy = [ry[p[1]] for p in pairs]
    mx, my = sum(dx) / n, sum(dy) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(dx, dy))
    vx = sum((a - mx) ** 2 for a in dx)
    vy = sum((b - my) ** 2 for b in dy)
    if not vx or not vy:
        return None
    return round(cov / math.sqrt(vx * vy), 3)


def screen(rows: list[dict], factors: list[str] | None = None) -> list[dict]:
    from bneck2 import lab as L
    factors = factors or [k for k in
                          ("f_mom_20", "f_burst", "f_attack", "f_hn",
                           "f_short", "f_conv", "f_B")]
    out = []
    for f in factors:
        ic = spearman([r.get(f) for r in rows],
                      [r.get("fwd_20") for r in rows])
        n = sum(1 for r in rows
                if r.get(f) is not None and r.get("fwd_20") is not None)
        w = L.wilson(sum(1 for r in rows if (r.get(f) or 0) > 0
                         and (r.get("fwd_20") or 0) > 0),
                     max(n, 1)) if n else {"lo": 0.0}
        out.append({"factor": f, "IC": ic, "n": n,
                    "hit_lo": w.get("lo", 0.0)})
    out.sort(key=lambda r: -(abs(r["IC"] or 0)))
    return out


def composite(rows: list[dict], factors: list[str],
              signs: dict[str, float] | None = None) -> list[dict]:
    """Equal-weight z-scores of winning factors. Signs MUST come from TRAIN
    only (pass signs=); computing them here on the same rows is in-sample."""
    stats = {}
    for f in factors:
        vals = [r[f] for r in rows if r.get(f) is not None]
        mu = sum(vals) / len(vals) if vals else 0.0
        sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 if vals else 1.0
        stats[f] = (mu, sd or 1.0)
    if signs is None:
        signs = {f: 1.0 if (spearman([r.get(f) for r in rows],
                                     [r.get("fwd_20") for r in rows]) or 0) >= 0 else -1.0
                 for f in factors}
    out = []
    for r in rows:
        z, k = 0.0, 0
        for f in factors:
            if r.get(f) is not None:
                mu, sd = stats[f]
                z += signs[f] * (r[f] - mu) / sd
                k += 1
        out.append({**r, "score": round(z / k, 4) if k else 0.0})
    return out


def composite_by_date(rows: list[dict], factors: list[str],
                      signs: dict[str, float] | None = None) -> list[dict]:
    """Per-rebalance-date cross-sectional z-scores (no look-ahead: each
    date standardized on its own cross-section only)."""
    out = []
    by_date: dict[str, list[dict]] = {}
    for r in rows:
        by_date.setdefault(str(r.get("date")), []).append(r)
    for d in sorted(by_date):
        out.extend(composite(by_date[d], factors, signs))
    return out
