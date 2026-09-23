"""bneck2 scarcity — breakthrough text -> implied bottleneck nodes + tickers.

Generalizes stockify's SCARCITY_MAP (stockify/services/detector.py,
quantum-scarcity thesis: breakthrough claims imply physical requirements,
which imply tickers) from quantum-only to every graph_v2 node.

Two keyword sources, kept distinct:
  PORTED_MAP — verbatim rows from stockify's SCARCITY_MAP (quantum stack).
  NODE_KEYWORDS — derived per node from label + kill_signals + destroy_paths.
    Tickers come from the node itself, so new nodes are covered automatically.

Pure + stdlib. No network. scan_text() is the single entry point.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "data" / "bottlenecks" / "graph_v2.json"

# (layer, keywords, tickers) — ported from stockify/services/detector.py
PORTED_MAP: list[tuple[str, list[str], list[str]]] = [
    ("quantum fabrication", ["fab", "foundry", "manufacturing", "cryogenic cmos", "packaging"], ["GFS"]),
    ("wafer test", ["wafer", "cryogenic test", "probing", "yield", "4 kelvin", "millikelvin"], ["FORM"]),
    ("qubit control", ["control", "readout", "microwave", "rf ", "metrology", "benchmark"], ["KEYS"]),
    ("cryogenics", ["dilution refrigerator", "cryostat", "millikelvin", "bluefors"], ["OXIG"]),
    ("photonics", ["photonic", "laser", "optical interconnect", "pic "], ["COHR", "LITE"]),
    ("trapped ion", ["trapped ion", "ionq", "quantinuum"], ["IONQ", "QNT"]),
    ("superconducting", ["superconducting", "transmon"], ["RGTI"]),
    ("annealing", ["anneal", "d-wave", "dwave"], ["QBTS"]),
    ("pq migration", ["post-quantum", "pqc", "q-day", "nists", "ml-dsa", "ml-kem"], ["ETH"]),
    ("pq token", ["quantum-resistant ledger", "qrl", "qanplatform", "cellframe"], ["QRL", "QANX", "CELL"]),
]

_STOP = {"the", "and", "for", "with", "from", "into", "scale", "large"}


def node_keywords(node: dict) -> list[str]:
    """Keyword phrases for a node: label words + kill/destroy signal phrases."""
    words = [w.strip("(),").lower() for w in node.get("label", "").split()]
    keys = [w for w in words if len(w) > 3 and w not in _STOP]
    for sig in list(node.get("kill_signals", [])) + list(node.get("destroy_paths", [])):
        s = str(sig).lower()
        keys.append(s)
        for w in s.replace("/", " ").replace("-", " ").split():
            if len(w) > 4 and w not in _STOP:
                keys.append(w)
    seen: list[str] = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    return seen


def build_map(graph: dict | None = None) -> list[dict]:
    """Full scan map: ported quantum rows (tagged) + one row per graph node."""
    rows = [{"layer": layer, "keywords": kws, "tickers": ticks,
             "node_id": "", "source": "stockify-port"}
            for layer, kws, ticks in PORTED_MAP]
    if graph is None:
        try:
            graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            graph = {"nodes": []}
    for n in graph.get("nodes", []):
        rows.append({"layer": n.get("label", n.get("id", "")),
                     "keywords": node_keywords(n),
                     "tickers": list(n.get("tickers", [])),
                     "node_id": n.get("id", ""),
                     "source": "graph_v2"})
    return rows


def scan_text(text: str, rows: list[dict] | None = None) -> list[dict]:
    """Return [{layer, node_id, tickers}] hits for text (case-insensitive)."""
    text = (text or "").lower()
    if not text.strip():
        return []
    rows = rows if rows is not None else build_map()
    hits = []
    for r in rows:
        if any(k and k in text for k in r["keywords"]):
            hits.append({"layer": r["layer"], "node_id": r["node_id"],
                         "tickers": [t for t in r["tickers"]]})
    return hits


def implied_tickers(text: str, rows: list[dict] | None = None) -> list[str]:
    out: list[str] = []
    for h in scan_text(text, rows):
        for t in h["tickers"]:
            if t not in out:
                out.append(t)
    return out
