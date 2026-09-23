"""FINRA short-data collector — per-symbol short flow, keyless ($0).

Endpoints (recipes ex-third_party/openinsider-mcp):
- Daily short volume (yesterday's tape):
  https://cdn.finra.org/equity/regsho/daily/{venue}shvol{YYYYMMDD}.txt
  venues probed in order: CNMS, NYSE, NMSQ... (first 200 wins).
  Columns: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market.
- Biweekly short interest:
  https://cdn.finra.org/equity/otcmarket/biweekly/shrt{YYYYMMDD}.csv
  (OTC leg; NASDAQ/NYSE SI via same CDN family — probed, else queued).

Email-format UA per FINRA CDN norms. CloudFront 403 = file not published
yet (not a ban): walk back trading days. Never raises.
"""
from __future__ import annotations

import datetime
import urllib.request
from pathlib import Path

UA = {"User-Agent": "bneck research contact@localhost",
      "Accept": "text/plain, */*"}

VENUES = ("CNMS", "NYSE", "NMSQ")


def _fetch(url: str, timeout: int = 30) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "bneck research contact@localhost",
            "Accept": "text/plain, */*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def _recent_dates(n: int = 6) -> list[str]:
    out, d = [], datetime.date.today()
    while len(out) < n:
        d -= datetime.timedelta(days=1)
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
    return out


def daily_short(tickers: list[str], timeout: int = 30) -> dict:
    """{ticker: {date, short_ratio, short_vol, total_vol}} latest found day."""
    want = {t.upper() for t in tickers}
    for day in _recent_dates():
        for venue in VENUES:
            body = _fetch(f"https://cdn.finra.org/equity/regsho/daily/"
                          f"{venue}shvol{day}.txt", timeout)
            if not body or "ShortVolume" not in body:
                continue
            agg: dict[str, dict] = {}
            for line in body.splitlines()[1:]:
                parts = line.split("|")
                if len(parts) < 5 or parts[1].upper() not in want:
                    continue
                try:
                    sv = float(parts[2])
                    tv = float(parts[4])
                except ValueError:
                    continue
                a = agg.setdefault(parts[1].upper(),
                                   {"short": 0.0, "total": 0.0})
                a["short"] += sv
                a["total"] += tv
            if agg:
                return {t: {"date": f"{day[:4]}-{day[4:6]}-{day[6:]}",
                            "short_ratio": round(v["short"] / v["total"], 4)
                            if v["total"] else 0.0,
                            "short_vol": int(v["short"]),
                            "total_vol": int(v["total"])}
                        for t, v in agg.items()}
    return {}


def _parse_day(body: str, want: set[str]) -> dict[str, dict]:
    agg: dict[str, dict] = {}
    for line in body.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 5 or parts[1].upper() not in want:
            continue
        try:
            sv, tv = float(parts[2]), float(parts[4])
        except ValueError:
            continue
        a = agg.setdefault(parts[1].upper(), {"short": 0.0, "total": 0.0})
        a["short"] += sv
        a["total"] += tv
    return {t: {"short_ratio": round(v["short"] / v["total"], 4) if v["total"] else 0.0}
            for t, v in agg.items()}


def short_history(tickers: list[str], dates: list[str],
                  timeout: int = 30) -> dict[str, dict[str, float | None]]:
    """Short ratios per ticker per asof-date (walks back to nearest tape).
    One file per date covers all tickers. Returns {date: {ticker: ratio}}."""
    import datetime as _dt
    want = {t.upper() for t in tickers}
    out: dict[str, dict[str, float | None]] = {}
    for asof in dates:
        y, m, d = map(int, asof.split("-"))
        day = _dt.date(y, m, d)
        found = None
        for _ in range(10):
            day -= _dt.timedelta(days=1)
            if day.weekday() >= 5:
                continue
            ds = day.strftime("%Y-%m-%d")
            for venue in VENUES:
                body = short_file(ds, venue, timeout)
                if body:
                    found = (ds, body)
                    break
            if found:
                break
        if not found:
            out[asof] = {t: None for t in tickers}
            continue
        parsed = _parse_day(found[1], want)
        out[asof] = {t: parsed.get(t.upper(), {}).get("short_ratio")
                     for t in tickers}
    return out


def short_file(day: str, venue: str = "CNMS", timeout: int = 30) -> str | None:
    """Raw tape for a date, cached forever (historical tapes immutable)."""
    import hashlib as _h
    import json as _j
    key = f"finra-{venue}-{day}"
    cache = Path(__file__).resolve().parents[1] / "data" / "cache"
    meta = cache / (key + ".meta.json")
    blob = cache / (key + ".txt")
    if blob.exists() and meta.exists():
        try:
            if _j.loads(meta.read_text()).get("rows", 0) > 100:
                return blob.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
    body = _fetch(f"https://cdn.finra.org/equity/regsho/daily/"
                  f"{venue}shvol{day.replace('-', '')}.txt", timeout)
    if not body or "ShortVolume" not in body:
        return None
    cache.mkdir(parents=True, exist_ok=True)
    blob.write_text(body, encoding="utf-8")
    meta.write_text(_j.dumps({"rows": body.count("\n"), "venue": venue}))
    return body
