"""Semantic Scholar collector — 2nd paper source, 429-aware ($0, keyless).

Shared unauth pool (100 req/5min) 429s often: retry with backoff (3 tries:
2s, 8s), then yield [] and let OpenAlex carry the pass. Never raises.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

API = "https://api.semanticscholar.org/graph/v1/paper/search"
UA = {"User-Agent": "bneck research contact@localhost"}


def search_url(query: str, limit: int = 20) -> str:
    return (f"{API}?{urllib.parse.urlencode({'query': query, 'limit': limit, 'fields': 'title,year,citationCount,authors'})}")


def fetch_papers(query: str, limit: int = 20, timeout: int = 25) -> list[dict]:
    last = None
    for wait in (0, 2, 8):
        if wait:
            time.sleep(wait)
        try:
            req = urllib.request.Request(search_url(query, limit), headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
            out = []
            for p in doc.get("data", []):
                out.append({"title": str(p.get("title", ""))[:160],
                            "year": p.get("year"),
                            "citations": p.get("citationCount", 0) or 0,
                            "authors": len(p.get("authors", []) or [])})
            out.append({"_ok": True})
            return out
        except Exception as exc:
            last = exc
            continue
    return [{"_ok": False, "error": str(last)[:100] if last else "failed"}]


def citation_mass(papers: list[dict]) -> dict:
    rows = [p for p in papers if "title" in p]
    return {"papers": len(rows),
            "citations": sum(p.get("citations", 0) for p in rows),
            "ok": any(p.get("_ok") for p in papers)}
