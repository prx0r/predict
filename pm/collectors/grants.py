"""Grants.gov collector — grant feed for digger/attack funding ($0, keyless).

Complements USAspending (contracts) with research grants: who funds
substitution research (photonic packaging, thermodynamic compute...).
"""
from __future__ import annotations

import json
import urllib.request

API = "https://api.grants.gov/v1/api/search2"


def search_body(keyword: str, rows: int = 20) -> dict:
    return {"keyword": keyword, "oppStatuses": ["forecasted", "posted"],
            "sortBy": "openDate|desc", "rows": rows, "offset": 0}


def parse_opps(doc: dict) -> list[dict]:
    out = []
    data = doc.get("data") or {}
    for o in data.get("oppHits", []):
        out.append({"id": o.get("id", ""), "title": o.get("title", "")[:160],
                    "agency": o.get("agencyName", ""),
                    "status": o.get("oppStatus", ""),
                    "open": o.get("openDate", ""), "close": o.get("closeDate", "")})
    return out


def fetch_opps(keyword: str, timeout: int = 30) -> list[dict]:
    try:
        req = urllib.request.Request(
            API, data=json.dumps(search_body(keyword)).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        return parse_opps(doc)
    except Exception:
        return []
