"""OpenAlex collector — AttackIntensity(b) velocity ($0, keyless).

papers/year reducing requirement for X, authors entering, citation
velocity, grants. A bottleneck with Scarcity up AND AttackIntensity up-up
is fantastic-earnings + deteriorating-terminal-value = reversal zone.
mailto= param gets the polite pool.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import Counter

API = "https://api.openalex.org/works"


def search_url(query: str, year_from: int = 2020, per_page: int = 50) -> str:
    q = urllib.parse.urlencode(
        {"search": query, "filter": f"from_publication_date:{year_from}-01-01",
         "per-page": per_page, "mailto": "bneck@localhost"})
    return f"{API}?{q}"


def parse_velocity(doc: dict) -> dict:
    """papers/year + top authors/institutions from one search page."""
    years: Counter = Counter()
    authors: Counter = Counter()
    for w in doc.get("results", []):
        y = w.get("publication_year")
        if y:
            years[y] += 1
        for a in w.get("authorships", [])[:8]:
            name = ((a.get("author") or {}).get("display_name")) or ""
            if name:
                authors[name] += 1
    total = doc.get("meta", {}).get("count", sum(years.values()))
    return {"total_works": total, "per_year": dict(sorted(years.items())),
            "top_authors": authors.most_common(10)}


def fetch_velocity(query: str, timeout: int = 30) -> dict:
    try:
        req = urllib.request.Request(search_url(query),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        out = parse_velocity(doc)
        out["ok"] = True
        return out
    except Exception:
        return {"total_works": 0, "per_year": {}, "top_authors": [],
                "ok": False}


def yearly_url(query: str, year_from: int = 2016) -> str:
    """True yearly counts via group_by (not the 50-row sample page)."""
    q = urllib.parse.urlencode(
        {"search": query, "filter": f"from_publication_date:{year_from}-01-01",
         "group_by": "publication_year", "per-page": 200,
         "mailto": "bneck@localhost"})
    return f"{API}?{q}"


def parse_yearly(doc: dict) -> dict:
    counts = {}
    for g in doc.get("group_by", []):
        try:
            counts[int(g.get("key"))] = int(g.get("count", 0))
        except (ValueError, TypeError):
            continue
    return {"per_year": dict(sorted(counts.items())),
            "total_works": sum(counts.values())}


def fetch_yearly(query: str, timeout: int = 30) -> dict:
    import datetime as _dt
    from bneck2 import lab as _LAB
    week = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-W%V")
    ckey = _LAB.cache_key("openalex", query, week)
    hit = _LAB.cache_get(ckey)
    if isinstance(hit, dict) and hit.get("ok"):
        return hit
    try:
        req = urllib.request.Request(yearly_url(query),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        out = parse_yearly(doc)
        out["ok"] = True
        try:
            _LAB.cache_set(ckey, out)
        except Exception:
            pass
        return out
    except Exception:
        return {"total_works": 0, "per_year": {}, "ok": False}
