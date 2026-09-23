"""Frontier-lab RSS collector — capability announcements ($0, keyless).

Lab blogs are primary-source capability events (J_t candidates). RSS
avoids JS walls. FEEDS maps what resolves; 404s stay queued, not faked.
"""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "bneck research contact@localhost"}

FEEDS = {
    "openai": "https://openai.com/news/rss.xml",
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "meta": "https://about.fb.com/news/rss/",
    # Queued (paths unresolved 2026-09-10): anthropic, xai.
}


def fetch_feed(url: str, timeout: int = 30) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        root = ET.fromstring(body)
        out = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "")[:160]
            pub = item.findtext("pubDate") or ""
            link = item.findtext("link") or ""
            if title:
                out.append({"title": title, "date": pub[:16], "link": link})
        return out
    except Exception:
        return []


def lab_posts(lab: str = "openai", limit: int = 30) -> list[dict]:
    url = FEEDS.get(lab, "")
    if not url:
        return []
    return fetch_feed(url)[:limit]


def capability_hits(posts: list[dict],
                    keywords=("agent", "reasoning", "robot", "science", "breakthrough",
                              "frontier", "autonom", "quantum", "coding")) -> list[dict]:
    return [p for p in posts
            if any(k in p["title"].lower() for k in keywords)]
