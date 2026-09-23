"""Hugging Face collector — implementation evidence, keyless reads ($0).

huggingface.co/api/models: model counts + likes per query/tag. Rising
open-model counts around a capability = implementation convergence
(pack: GitHub/HF queries). Sort by likes surfaces what builders use.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def search_url(query: str, limit: int = 20) -> str:
    return ("https://huggingface.co/api/models"
            f"?{urllib.parse.urlencode({'search': query, 'limit': limit, 'sort': 'likes', 'direction': '-1'})}")


def parse_models(doc: list) -> list[dict]:
    out = []
    for m in doc if isinstance(doc, list) else []:
        out.append({"id": m.get("id", ""), "likes": m.get("likes", 0) or 0,
                    "downloads": m.get("downloads", 0) or 0,
                    "tags": [t for t in (m.get("tags") or [])[:8]]})
    return out


def fetch_models(query: str, limit: int = 20, timeout: int = 25) -> list[dict]:
    try:
        req = urllib.request.Request(search_url(query, limit),
                                     headers={"User-Agent": "bneck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_models(json.loads(r.read().decode("utf-8", "replace")))
    except Exception:
        return []


def implementation_heat(models: list[dict]) -> dict:
    n = len(models)
    likes = sum(m["likes"] for m in models)
    return {"models": n, "likes": likes,
            "heat": "HIGH" if (n >= 15 and likes >= 5000) else
                    "WARM" if (n >= 5 and likes >= 500) else "quiet"}
