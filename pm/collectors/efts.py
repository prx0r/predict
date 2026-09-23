"""EFTS full-text search collector — filings mentioning X ($0, keyless).

https://efts.sec.gov/LATEST/search-index (GET, q + forms params).
Finds filings mentioning drugs/tech/risks (mcp-edgar recipe). Bounded.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://efts.sec.gov/LATEST/search-index"
UA = {"Accept": "application/json", "User-Agent": "bneck"}


def search(term: str, forms: str = "10-K,10-Q,8-K", limit: int = 20,
           timeout: int = 30) -> list[dict]:
    try:
        url = f"{API}?{urllib.parse.urlencode({'q': term, 'forms': forms})}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        out = []
        for h in doc.get("hits", {}).get("hits", [])[:limit]:
            s = h.get("_source", {})
            names = s.get("display_names") or ["?"]
            out.append({"date": s.get("file_date", "")[:10],
                        "form": s.get("form", ""),
                        "company": str(names[0])[:60],
                        "cik": s.get("cik", "")})
        return out
    except Exception:
        return []


def count(term: str, forms: str = "10-K,10-Q,8-K") -> dict:
    try:
        url = f"{API}?{urllib.parse.urlencode({'q': term, 'forms': forms})}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        tot = doc.get("hits", {}).get("total", 0)
        val = tot.get("value", 0) if isinstance(tot, dict) else tot
        return {"term": term, "total": val}
    except Exception:
        return {"term": term, "total": None}
