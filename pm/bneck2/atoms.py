"""bneck2 atoms — AI-to-Atoms index + LPKF-like screen (goated §§10-14, 38).

Universe: test / measurement / characterization / automation / control /
verification / certification — the interface layer where bits become atoms
and atoms become trustworthy bits (data/universe/ai_atoms.json).

Screen (thesis §10 shape): small current cashflows + potential critical
future node. Convexity = node severity x cross-world breadth / revenue
scale, minus crowdedness penalty. Revenue figures are rough 2025 sellers'
claims from the thesis, flagged estimated — the screen ranks *shapes*,
not valuations. Never a buy list.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "universe" / "ai_atoms.json"


def load_universe(path: Path = UNIVERSE_PATH) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("companies", [])
    except (OSError, ValueError):
        return []


def convexity(c: dict, severity_by_node: dict[str, float],
              crowded: dict[str, float] | None = None) -> dict:
    """Convexity = mean(B over linked nodes) x breadth / log-revenue scale."""
    crowded = crowded or {}
    nodes = c.get("nodes", [])
    b = sum(severity_by_node.get(n, 0.0) for n in nodes) / max(len(nodes), 1)
    breadth = len(set(nodes))
    rev = max(float(c.get("rev_usd_m", 0) or 0), 1.0)
    scale = math.log10(rev + 10.0)
    crowd = sum(float(crowded.get(n, 0.0)) for n in nodes) / max(len(nodes), 1)
    score = (b * (1 + 0.25 * (breadth - 1)) / scale) * (1 - 0.5 * crowd)
    return {"ticker": c.get("ticker"), "layer": c.get("layer"),
            "nodes": nodes, "breadth": breadth,
            "convexity": round(score, 4), "crowdedness": round(crowd, 3),
            "note": c.get("note", "")}


def screen(companies: list[dict] | None = None,
           severity_by_node: dict[str, float] | None = None,
           crowded: dict[str, float] | None = None) -> list[dict]:
    if companies is None:
        companies = load_universe()
    rows = [convexity(c, severity_by_node or {}, crowded) for c in companies]
    rows.sort(key=lambda r: -r["convexity"])
    return rows
