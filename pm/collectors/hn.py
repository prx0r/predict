"""Hacker News collector — expert/community chatter, keyless ($0).

Algolia HN API (no key): stories matching a node query with points,
comments, recency. Used for narrative-saturation reads (crowdedness
cross-check), never as evidence of technical truth.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://hn.algolia.com/api/v1/search"


def search_url(query: str, limit: int = 20) -> str:
    return f"{API}?{urllib.parse.urlencode({'query': query, 'tags': 'story', 'hitsPerPage': limit})}"


def parse_hits(doc: dict) -> list[dict]:
    out = []
    for h in doc.get("hits", []):
        out.append({"title": (h.get("title") or "")[:160],
                    "points": h.get("points", 0) or 0,
                    "comments": h.get("num_comments", 0) or 0,
                    "date": (h.get("created_at") or "")[:10],
                    "url": h.get("url", "") or ""})
    return out


def narrative_heat(hits: list[dict]) -> dict:
    """Saturation proxy: volume x engagement. High heat + high crowdedness
    corroborates; high heat + low crowdedness flags stale crowdedness."""
    n = len(hits)
    pts = sum(h["points"] for h in hits)
    return {"stories": n, "points": pts,
            "heat": "HIGH" if (n >= 10 and pts >= 500) else
                    "WARM" if (n >= 4 and pts >= 100) else "quiet"}


def fetch_stories(query: str, limit: int = 20, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(search_url(query, limit),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_hits(json.loads(r.read().decode("utf-8", "replace")))
    except Exception:
        return []
