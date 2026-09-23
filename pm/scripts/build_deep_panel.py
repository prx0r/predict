#!/usr/bin/env python3
"""Deep weekly panel (2y, NVDA-led universe) for serious backtesting.

Weekly Friday grid x tickers x point-in-time factors. Slow first run
(FINRA tapes cache forever after; Yahoo cached daily; HN live per cell).
Usage: /usr/bin/python3 scripts/build_deep_panel.py [--weeks 104]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UNIVERSE = ["NVDA", "AMD", "MU", "AVGO", "GOOGL", "META"]


def fridays(n: int) -> list[str]:
    today = date.today()
    fri = today - timedelta(days=(today.weekday() - 4) % 7)
    return [(fri - timedelta(weeks=k)).isoformat()
            for k in range(n - 1, -1, -1)]


def main() -> int:
    from bneck2 import predict as PD
    from collectors import finra as FIN
    from collectors import hn as HN
    from bneck2 import killfeed as K
    weeks = 104
    if "--weeks" in sys.argv:
        weeks = int(sys.argv[sys.argv.index("--weeks") + 1])
    dates = fridays(weeks)
    hist = {t: {d: c for d, c in PD._closes(t)} for t in UNIVERSE}
    shorts = FIN.short_history(UNIVERSE, dates)
    hn_q = {"NVDA": "Nvidia"}
    hn: dict[str, dict[str, int]] = {}
    for t, q in hn_q.items():
        hn[t] = {}
        for d in dates:
            hn[t][d] = -1  # filled below in one bounded sweep
    # bounded HN sweep: NVDA weekly counts (104 calls max)
    import calendar
    import datetime as _dt
    import urllib.parse
    import urllib.request
    for i, d in enumerate(dates):
        lo = dates[i - 1] if i else (date.fromisoformat(d) - timedelta(days=7)).isoformat()
        try:
            lo_ts = calendar.timegm(_dt.datetime.fromisoformat(lo).timetuple())
            hi_ts = calendar.timegm(_dt.datetime.fromisoformat(d).timetuple())
            url = ("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
                {"query": "Nvidia", "tags": "story",
                 "numericFilters": f"created_at_i>{lo_ts},created_at_i<{hi_ts}",
                 "hitsPerPage": 1}))
            req = urllib.request.Request(url, headers={"User-Agent": "bneck"})
            with urllib.request.urlopen(req, timeout=20) as r:
                hn["NVDA"][d] = int(json.loads(r.read().decode("utf-8", "replace")).get("nbHits", 0))
        except Exception:
            hn["NVDA"][d] = 0
        time.sleep(0.2)
    rows = []
    for d in dates:
        for t in UNIVERSE:
            cl = sorted(hist.get(t, {}).items())
            if not cl:
                continue
            idx = next((k for k, (dd, _) in enumerate(cl) if dd > d), None)
            if idx is None or idx < 20 or idx + 20 >= len(cl):
                fwd = None
            else:
                a, b = cl[idx - 1][1], cl[idx + 19][1]
                fwd = round((b - a) / a, 4)
            past = [(dd, c) for dd, c in cl if dd <= d]
            mom = round((past[-1][1] - past[-21][1]) / past[-21][1], 4) if len(past) >= 21 and past[-21][1] else None
            sec = PD.sec_counts_30d(K.CIK_MAP[t], d) if t in K.CIK_MAP else {"n30": None, "med": None}
            rows.append({"date": d, "ticker": t,
                         "f_mom_20": mom,
                         "f_burst": (sec["n30"] / max(sec["med"] or 0, 1)
                                     if sec["n30"] is not None else None),
                         "f_short": shorts.get(d, {}).get(t),
                         "f_hn": hn.get(t, {}).get(d),
                         "fwd_20": fwd})
    out = ROOT / "data" / "predict" / "deep-weekly.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    good = sum(1 for r in rows if r["fwd_20"] is not None)
    print(f"deep panel: {len(rows)} rows, {good} with forwards -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
