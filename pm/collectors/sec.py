"""SEC EDGAR collector — filings as a real-time event stream ($0, keyless).

Submissions JSON updates in under a second; XBRL under a minute.
Tracks: Form 4 (insider), 13D/G (activist), 8-K (deals), 10-K/Q (backlog,
inventory, risk-factor language). Requires descriptive User-Agent.
"""
from __future__ import annotations

import json
import urllib.request

UA = {"User-Agent": "bneck research contact@localhost", "Accept": "application/json"}


def submissions_url(cik: str) -> str:
    return f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"


def parse_recent_filings(doc: dict, forms=("4", "13D", "13G", "8-K"),
                         limit: int = 20) -> list[dict]:
    out = []
    filings = (doc.get("filings") or {}).get("recent") or {}
    n = len(filings.get("form", []))
    for i in range(min(n, 500)):
        if filings["form"][i] not in forms:
            continue
        out.append({"form": filings["form"][i],
                    "filingDate": filings.get("filingDate", [""])[i],
                    "accession": filings.get("accessionNumber", [""])[i],
                    "primaryDoc": filings.get("primaryDocument", [""])[i]})
        if len(out) >= limit:
            break
    return out


def fetch_recent_filings(cik: str, forms=("4", "13D", "13G", "8-K"),
                         limit: int = 20, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(submissions_url(cik), headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        return parse_recent_filings(doc, forms, limit)
    except Exception:
        return []
