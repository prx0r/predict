"""Crossref collector — funder/grant links per work ($0, keyless polite).

Who funds the attack research (thesis: follow the money behind
substitution). Polite pool via mailto. Bounded, never raises.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "bneck (mailto:bneck@localhost)"}


def search_works(query: str, rows: int = 10, timeout: int = 25) -> list[dict]:
    try:
        url = ("https://api.crossref.org/works"
               f"?{urllib.parse.urlencode({'query': query, 'rows': rows, 'mailto': 'bneck@localhost'})}")
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        out = []
        for w in ((doc.get("message") or {}).get("items") or []):
            funders = [f.get("name", "") for f in (w.get("funder") or [])]
            out.append({"title": "".join(w.get("title", [""]))[:160],
                        "year": (w.get("published", {}).get("date-parts", [[None]])[0][0]),
                        "cited_by": w.get("is-referenced-by-count", 0),
                        "funders": [f for f in funders if f][:3],
                        "doi": w.get("DOI", "")})
        return out
    except Exception:
        return []
