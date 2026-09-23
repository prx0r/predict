"""Jobs collector — hiring clusters as frontier-lab signal ($0, keyless).

Pack thesis: hiring clusters in a new technical domain = revealed
preference (Phase 1). Greenhouse boards API is public per-board;
correct slugs only (openai/lever slugs 404 — queued, not guessed).
"""
from __future__ import annotations

import json
import urllib.request
from collections import Counter

UA = {"User-Agent": "bneck research contact@localhost"}

BOARDS = {
    # Greenhouse board slug -> lab label (verified live 2026-09-10).
    "anthropic": "Anthropic",
}


def fetch_board(board: str, timeout: int = 30) -> list[dict]:
    try:
        req = urllib.request.Request(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=false",
            headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        return doc.get("jobs", []) if isinstance(doc, dict) else []
    except Exception:
        return []


CLUSTERS = {
    "research": ("research", "scientist", "fellow", "phd"),
    "silicon": ("silicon", "chip", "hardware", "asic", "gpu", "tpu"),
    "robotics": ("robot", "mechanical", "actuat", "motor"),
    "infra": ("infrastructure", "datacenter", "data center", "sre", "network"),
    "energy": ("energy", "power", "nuclear", "grid"),
    "safety": ("safety", "alignment", "policy", "assurance"),
    "bio": ("bio", "lab", "wetlab", "chemistry"),
    "frontier-models": ("frontier", "pretraining", "post-training", "post training"),
}


def cluster_counts(jobs: list[dict]) -> dict:
    titles = [str(j.get("title", "")).lower() for j in jobs]
    hits: dict[str, int] = {}
    for cluster, keys in CLUSTERS.items():
        hits[cluster] = sum(1 for t in titles if any(k in t for k in keys))
    return {"total": len(jobs),
            "by_cluster": {k: v for k, v in
                           sorted(hits.items(), key=lambda kv: -kv[1]) if v}}


def hiring_cluster(board: str = "anthropic") -> dict:
    jobs = fetch_board(board)
    out = cluster_counts(jobs)
    out["board"] = board
    return out
