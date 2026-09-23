#!/usr/bin/env python3
"""Import the R2 resource pack into bneck2 stores (idempotent, deduped).

Merges (never overwrites engineer-curated rows):
  pack config/frontier_lab_capital_events.json -> data/labs/commitments.json
  pack resources/digger_watchlist.json        -> data/labs/diggers.json
Watch/benchmark event kinds route to diggers/unknowns, NOT commitments.
Usage: /usr/bin/python3 scripts/import_pack.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PACK = ROOT / "imported" / "resource_pack"


def load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


REL = {"Very high": 1.0, "High": 0.9, "Medium": 0.6, "Watch": 0.4}


def kind_map(kind: str) -> tuple[str, int] | None:
    """(commitment_kind, duration_years) or None (=not a commitment)."""
    k = kind.lower()
    if "nuclear" in k:
        return ("multidecade-contract", 22)
    if any(s in k for s in ("benchmark", "milestone", "watch")):
        return None
    if any(s in k for s in ("silicon", "chip")):
        return ("silicon-roadmap", 10)
    if "acquisit" in k or "combination" in k:
        return ("acquisition", 3)
    return ("deployment", 5)


def import_events() -> tuple[int, int]:
    doc = load(PACK / "config" / "frontier_lab_capital_events.json", [])
    events = doc if isinstance(doc, list) else doc.get("events", doc)
    path = ROOT / "data" / "labs" / "commitments.json"
    cur = load(path, {"commitments": []})
    have = {(c.get("lab"), c.get("target")) for c in cur["commitments"]}
    added = skipped = 0
    for e in events:
        mapped = kind_map(e.get("event_type", ""))
        if mapped is None:
            skipped += 1
            continue
        kind, dur = mapped
        key = (e.get("frontier_actor"), e.get("counterparty_or_target"))
        if key in have:
            continue
        spec = 0.9 if any(s in (e.get("counterparty_or_target", "") + e.get("observable", "")).lower()
                          for s in ("silicon", "nuclear", "tpu", "trainium")) else 0.7
        cur["commitments"].append({
            "lab": e.get("frontier_actor"), "target": e.get("counterparty_or_target"),
            "kind": kind, "date": (e.get("date") or "2026-01-01")[:10],
            "duration_years": dur, "specificity": spec, "relevance": REL.get(e.get("signal_strength"), 0.5),
            "source": e.get("source_url", ""), "tag": "imported-pack",
            "note": f"{e.get('observable', '')} | {e.get('bottleneck_interpretation', '')}"[:300]})
        have.add(key)
        added += 1
    path.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    return added, skipped


def import_diggers() -> tuple[int, int]:
    doc = load(PACK / "resources" / "digger_watchlist.json", [])
    items = doc if isinstance(doc, list) else doc.get("diggers", doc)
    path = ROOT / "data" / "labs" / "diggers.json"
    cur = load(path, {"diggers": []})
    added = merged = 0
    for d in items:
        name = d.get("name", "")
        hit = next((x for x in cur["diggers"]
                    if name.lower() in x.get("name", "").lower()
                    or x.get("name", "").lower() in name.lower()), None)
        bar = list(d.get("proof_needed", []))
        if hit:
            have = set(hit.setdefault("bar", []))
            for b in bar:
                if b not in have:
                    hit["bar"].append(b)
                    merged += 1
        else:
            cur["diggers"].append({"name": name, "kind": "substrate",
                                   "targets_edge": "", "rung": "CLAIM",
                                   "note": d.get("why", "")[:300],
                                   "research": d.get("url", ""),
                                   "bar": bar})
            added += 1
    path.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    return added, merged


if __name__ == "__main__":
    a, s = import_events()
    d, m = import_diggers()
    print(f"commitments: +{a} added, {s} watch-kinds routed elsewhere")
    print(f"diggers: +{d} new, {m} proof-bars merged")
