"""Paper portfolio: NVDA timing rules vs buy-hold, forward from first run.

Appends one row per day to data/paper/nvda.csv:
  date, px, w_short, w_burst, eq_short, eq_burst, eq_bh1x
Rules frozen as of NORTHSTAR-5/E045 code (bneck2.nvda.size_rule).
Verdict E047 resolves after 90 days of rows. Run via cron with oneclick.
"""
from __future__ import annotations

import csv
import datetime
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bneck2 import nvda as NV  # noqa: E402
from bneck2 import prices as P  # noqa: E402
from collectors import finra as FIN  # noqa: E402
from collectors import sec as S  # noqa: E402


def _submissions(cik: str) -> list:
    req = urllib.request.Request(
        S.submissions_url(cik),
        headers={"User-Agent": "bneck research contact@localhost",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        doc = json.loads(r.read().decode("utf-8", "replace"))
    fl = (doc.get("filings") or {}).get("recent") or {}
    return [(f, d) for f, d in zip(fl.get("form", []), fl.get("filingDate", [])) if d]


def _burst(d: str, forms: list) -> float:
    def sh(x: str, n: int) -> str:
        y, m, dd = map(int, x.split("-"))
        return (datetime.date(y, m, dd) + datetime.timedelta(days=n)).isoformat()
    win = [f for f, fd in forms if fd and d >= fd >= sh(d, -30)]
    return sum(1 for f in win if f == "4") / 5.0 + sum(
        1 for f in win if f in ("8-K", "13D", "13G")) / 2.0


def main() -> dict:
    closes = {c["date"]: c["close"]
              for c in P.history("NVDA", "3mo").get("closes", [])}
    dates = sorted(closes)
    today = dates[-1]
    forms = _submissions("1045810")
    shorts = FIN.short_history(["NVDA"], dates)
    past = dates
    m20 = None
    if len(past) > 20 and closes[past[-21]]:
        m20 = (closes[past[-1]] - closes[past[-21]]) / closes[past[-21]]
    feats = {"mom_20": m20, "burst": _burst(today, forms),
             "short": (shorts.get(today) or {}).get("NVDA"), "hn": 0}
    w_s = NV.size_rule(feats, "short_fade")
    w_b = NV.size_rule(feats, "burst_fade")
    out = ROOT / "data" / "paper" / "nvda.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    prev = None
    if out.exists():
        rows = list(csv.DictReader(out.open()))
        if rows:
            prev = rows[-1]
    px = closes[today]
    if prev is None:
        row = {"date": today, "px": px, "w_short": w_s, "w_burst": w_b,
               "eq_short": 1.0, "eq_burst": 1.0, "eq_bh1x": 1.0}
    else:
        r = (px - float(prev["px"])) / float(prev["px"])
        pw_s, pw_b = float(prev["w_short"]), float(prev["w_burst"])
        row = {"date": today, "px": px, "w_short": w_s, "w_burst": w_b,
               "eq_short": float(prev["eq_short"]) * (1 + pw_s * r - abs(w_s - pw_s) * NV.COST),
               "eq_burst": float(prev["eq_burst"]) * (1 + pw_b * r - abs(w_b - pw_b) * NV.COST),
               "eq_bh1x": float(prev["eq_bh1x"]) * (1 + r)}
    if prev is None or prev["date"] != today:
        new = not out.exists()
        with out.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    return {"date": today, "px": px, "w_short": w_s, "w_burst": w_b,
            "eq_short": row["eq_short"], "eq_burst": row["eq_burst"],
            "eq_bh1x": row["eq_bh1x"]}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
