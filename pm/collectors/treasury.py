"""Treasury FiscalData collector — rates/debt/spending, keyless ($0).

api.fiscaldata.treasury.gov: average interest rates, debt outstanding,
receipts/outlays. Macro anchor for financing-life vs tech-life
(duration-mismatch shorts need the financing leg too).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
UA = {"User-Agent": "bneck research contact@localhost"}


def _get(path: str, params: dict, timeout: int = 25):
    try:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def avg_rates(page_size: int = 5) -> list[dict]:
    """Latest average interest rates by security (financing-life input)."""
    doc = _get("/v2/accounting/od/avg_interest_rates",
               {"sort": "-record_date", "page[size]": page_size}) or {}
    return [{"date": d.get("record_date", ""),
             "security": d.get("security_desc", ""),
             "rate": d.get("avg_interest_rate_amt", "")}
            for d in doc.get("data", [])]


def debt_outstanding() -> dict:
    doc = _get("/v2/accounting/od/debt_to_penny",
               {"sort": "-record_date", "page[size]": 1}) or {}
    rows = doc.get("data", [])
    if not rows:
        return {"total": None}
    return {"date": rows[0].get("record_date", ""),
            "total": rows[0].get("tot_pub_debt_out_amt", "")}
