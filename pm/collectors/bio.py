"""Bio validation collectors — ClinicalTrials.gov + openFDA ($0, keyless).

Trials = physical validation queue (thesis: what apparatus must every
candidate pass through). openFDA = deployment/permission events
(recalls, clearances). Bounded, never raise.
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


def trials_count(term: str) -> dict:
    """Total + recruiting studies for a term (validation demand proxy)."""
    doc = _get("https://clinicaltrials.gov/api/v2/studies"
               f"?{urllib.parse.urlencode({'query.term': term, 'countTotal': 'true', 'pageSize': 5})}")
    studies = ((doc or {}).get("studies") or [])
    recruiting = sum(1 for s in studies
                     if "RECRUIT" in str(((s.get("protocolSection") or {}).get("statusModule") or {}).get("overallStatus", "")).upper())
    return {"term": term, "total": (doc or {}).get("totalCount", 0),
            "recruiting_sample": recruiting, "sample": len(studies)}


def fda_counts(device_code: str = "") -> dict:
    """510k clearance counts (deployment permission flow)."""
    q = f"?{urllib.parse.urlencode({'search': f'product_code:{device_code}', 'limit': 1})}" if device_code else "?limit=1"
    doc = _get(f"https://api.fda.gov/device/510k.json{q}")
    meta = (doc or {}).get("meta", {})
    return {"total": meta.get("results", {}).get("total", 0)}
