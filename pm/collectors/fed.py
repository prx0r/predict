"""Federal data collectors — NSF, Federal Register, BLS, OSTI ($0, keyless).

All simple GET+JSON. Bounded, never raise.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "bneck research contact@localhost"}


def _get(url: str, timeout: int = 25):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def nsf_awards(keyword: str, limit: int = 10) -> list[dict]:
    """NSF award search: funding velocity per research direction."""
    doc = _get("https://www.research.gov/awardapi-service/v1/awards.json"
               f"?{urllib.parse.urlencode({'keyword': keyword, 'offset': 0})}")
    out = []
    for a in ((doc or {}).get("response", {}).get("award") or [])[:limit]:
        out.append({"title": str(a.get("title", ""))[:160],
                    "amount": a.get("estimatedTotalAmt"),
                    "agency": "NSF", "date": str(a.get("startDate", ""))[:10],
                    "awardee": a.get("awardeeName", "")[:60]})
    return out


def fedregister_docs(term: str, limit: int = 10) -> list[dict]:
    """Federal Register: permission/regulatory state (export, energy, AI)."""
    doc = _get("https://www.federalregister.gov/api/v1/documents.json"
               f"?{urllib.parse.urlencode({'per_page': limit, 'conditions[term]': term})}")
    out = []
    for d in ((doc or {}).get("results") or []):
        out.append({"title": str(d.get("title", ""))[:160],
                    "type": d.get("type", ""), "date": d.get("publication_date", ""),
                    "agency": ", ".join((d.get("agency_names") or [])[:2])})
    return out


def bls_series(series_id: str = "CUUR0000SA0") -> dict:
    """BLS CPI baseline (macro anchor for real-vs-nominal reads)."""
    doc = _get(f"https://api.bls.gov/publicAPI/v2/timeseries/data/{series_id}"
               "?startyear=2025&endyear=2026")
    try:
        data = doc["Results"]["series"][0]["data"]
        return {"series": series_id, "latest": data[0]}
    except (TypeError, KeyError, IndexError):
        return {"series": series_id, "latest": None}


def osti_records(title: str, rows: int = 10) -> list[dict]:
    """OSTI technical reports (DOE research adjacent to labs)."""
    doc = _get("https://www.osti.gov/api/v1/records"
               f"?{urllib.parse.urlencode({'title': title, 'rows': rows})}")
    out = []
    for r in doc or []:
        out.append({"title": str(r.get("title", ""))[:160],
                    "date": str(r.get("publication_date", ""))[:10],
                    "lab": r.get("site", "") or r.get("lab", "")})
    return out
