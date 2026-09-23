"""USAspending collector — slow-money clock: gov awards predate equity ($0, no auth).

Unexpected DOE/lab funding -> company -> technology -> bottleneck node
updates P(binding). Award search API v2.
"""
from __future__ import annotations

import json
import urllib.request

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def search_body(keyword: str, limit: int = 20) -> dict:
    return {"filters": {"keywords": [keyword], "award_type_codes": ["A", "B", "C", "D",
            "02", "03", "04", "05", "10", "06", "07", "08", "09", "11"]},
            "fields": ["Award ID", "Recipient Name", "Award Amount",
                       "Awarding Agency", "Award Type", "Start Date"],
            "limit": limit, "page": 1,
            "sort": "Award Amount", "order": "desc"}


def parse_awards(doc: dict) -> list[dict]:
    out = []
    for r in doc.get("results", []):
        out.append({"award_id": r.get("Award ID", ""),
                    "recipient": r.get("Recipient Name", ""),
                    "amount": r.get("Award Amount"),
                    "agency": r.get("Awarding Agency", ""),
                    "type": r.get("Award Type", ""),
                    "start": r.get("Start Date", "")})
    return out


def fetch_awards(keyword: str, limit: int = 20, timeout: int = 30) -> list[dict]:
    try:
        req = urllib.request.Request(
            API, data=json.dumps(search_body(keyword, limit)).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        return parse_awards(doc)
    except Exception:
        return []
