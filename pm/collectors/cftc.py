"""CFTC COT collector — futures positioning, keyless Socrata ($0).

publicreporting.cftc.gov/resource/jun7-fc8e.json (legacy futures-only,
no auth). Non-commercial net = speculative pressure gauge (regime input).
Recipe ex-third_party/financial-mcp (field map ported stdlib).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"
UA = {"User-Agent": "bneck", "Accept": "application/json"}

FIELDS = {
    "noncomm_positions_long_all": "nc_long",
    "noncomm_positions_short_all": "nc_short",
    "comm_positions_long_all": "c_long",
    "comm_positions_short_all": "c_short",
}


def _f(x) -> int:
    try:
        return int(float(x))
    except (ValueError, TypeError):
        return 0


def positioning(market: str, limit: int = 8, timeout: int = 30) -> list[dict]:
    """Recent COT rows for markets matching name (SoQL like, ci)."""
    try:
        q = (f"upper(market_and_exchange_names) like '%{market.upper()}%'")
        url = f"{API}?{urllib.parse.urlencode({'$limit': limit, '$where': q, '$order': 'report_date_as_yyyy_mm_dd DESC'})}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        out = []
        for row in doc if isinstance(doc, list) else []:
            nc = _f(row.get("noncomm_positions_long_all")) - _f(row.get("noncomm_positions_short_all"))
            oi = _f(row.get("open_interest_all"))
            out.append({"date": str(row.get("report_date_as_yyyy_mm_dd", ""))[:10],
                        "market": str(row.get("market_and_exchange_names", ""))[:70],
                        "nc_net": nc, "open_interest": oi,
                        "nc_pct_oi": round(nc / oi, 4) if oi else 0.0})
        return out
    except Exception:
        return []
