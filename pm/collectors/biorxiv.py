"""bioRxiv collector — preprint velocity for bio nodes, keyless ($0).

api.biorxiv.org/details/{server}/{from}/{to}/{cursor}/json. Counts +
server split per query window. Feeds AttackIntensity-adjacent preprint
reads where OpenAlex is slow (thesis: experimental scarcity starts in
preprints before journals).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import Counter


def window_url(server: str, start: str, end: str, cursor: int = 0) -> str:
    return (f"https://api.biorxiv.org/details/{server}/{start}/{end}/"
            f"{cursor}/json")


def fetch_counts(query: str, server: str = "biorxiv", start: str = "2026-01-01",
                 end: str = "2026-09-10", timeout: int = 30) -> dict:
    """Keyword-filtered preprint counts. NOTE: details endpoint returns a
    date window, not a search — we page (cap 5) and keyword-filter titles."""
    keys = [w.lower() for w in query.replace("/", " ").split() if len(w) > 3]
    total, hits, cats = 0, 0, Counter()
    cursor = 0
    try:
        for _ in range(5):
            req = urllib.request.Request(
                window_url(server, start, end, cursor),
                headers={"User-Agent": "bneck"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
            batch = doc.get("collection", [])
            if not batch:
                break
            total += len(batch)
            for p in batch:
                text = f"{p.get('title', '')} {p.get('category', '')}".lower()
                if any(k in text for k in keys):
                    hits += 1
                    cats[p.get("category", "?")] += 1
            cursor += len(batch)
    except Exception:
        return {"query": query, "window_hits": hits, "window_total": total,
                "ok": False}
    return {"query": query, "window_hits": hits, "window_total": total,
            "top_categories": cats.most_common(5), "ok": True}
