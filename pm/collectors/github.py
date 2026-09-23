"""GitHub collector — implementation evidence, not hype ($0, keyless base).

Watches dependency-graph repos for: pushes touching KV/attention/memory
paths, branch creation, releases. Unauthenticated: 60 req/hr; GITHUB_TOKEN
env raises to 5000/hr. Never clones in the collector (metadata only).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API = "https://api.github.com"


def _headers() -> dict:
    h = {"User-Agent": "bneck", "Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


def events_url(repo: str) -> str:
    return f"{API}/repos/{repo}/events?per_page=30"


def parse_implementation_signals(events: list[dict],
                                 keywords=("kv", "attention", "memory", "cache",
                                           "quant", "speculative", "cxl")) -> list[dict]:
    """PushEvents/ReleaseEvents whose commits/branches hit memory-path keywords."""
    out = []
    for e in events:
        if e.get("type") not in ("PushEvent", "ReleaseEvent", "CreateEvent"):
            continue
        payload = e.get("payload") or {}
        texts = []
        for c in payload.get("commits", [])[:5]:
            texts.append(c.get("message", ""))
        ref = payload.get("ref", "") or ""
        blob = " ".join(texts + [ref]).lower()
        hits = sorted({k for k in keywords if k in blob})
        if hits or e.get("type") == "ReleaseEvent":
            out.append({"repo": (e.get("repo") or {}).get("name", ""),
                        "type": e.get("type"), "ts": e.get("created_at", ""),
                        "actor": (e.get("actor") or {}).get("login", ""),
                        "keyword_hits": hits, "ref": ref})
    return out


def fetch_repo_signals(repo: str, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(events_url(repo), headers=_headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            events = json.loads(r.read().decode("utf-8", "replace"))
        return parse_implementation_signals(events)
    except Exception:
        return []
