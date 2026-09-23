"""Import ProphetMap layer stack as the dependency-graph backbone (stdlib).

Layers -> typed layer nodes (grade HYPOTHESIS, provenance prophetmap).
Tickers -> suppliers[] links on their layer node (companies last: tickers
never become physical nodes). Chain-A position order -> REQUIRES skeleton
edges (quarantined: layer order is a hypothesis about physical dependency,
not evidence). Idempotent: re-run replaces PML_ nodes/links.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bneck2 import edges as E  # noqa: E402

PM = ROOT / "third_party" / "prophetmap" / "data"
GRAPH = ROOT / "data" / "bottlenecks" / "graph_v2.json"


def main() -> dict:
    layers = json.loads((PM / "layers.json").read_text())
    uni = json.loads((PM / "universe.json").read_text())
    ls = layers if isinstance(layers, list) else layers.get("layers", [])
    us = uni if isinstance(uni, list) else uni.get("tickers", uni.get("universe", []))
    by_layer: dict[str, list] = {}
    for u in us:
        by_layer.setdefault(u.get("layer"), []).append(u)
    g = json.loads(GRAPH.read_text())
    keep = {n["id"]: n for n in g.get("nodes", [])
            if n.get("id", "").startswith("PML_")}
    nodes = [n for n in g.get("nodes", []) if not n.get("id", "").startswith("PML_")]
    for lyr in ls:
        lid = lyr.get("id")
        prev = keep.get(f"PML_{lid}", {})
        sups = [{"ticker": u.get("symbol"),
                 "exposure": u.get("layerRole"),
                 "moat_capture": u.get("moatCapture"),
                 "ai_contribution": u.get("aiContribution"),
                 "evidence": [{"value": "prophetmap universe.json",
                               "source": "third_party/prophetmap",
                               "date": "2026-09-10", "confidence": 0.5}]}
                for u in by_layer.get(lid, []) if u.get("symbol")]
        nodes.append({"id": f"PML_{lid}", "type": "layer",
                      "label": lyr.get("nameEn") or lyr.get("name"),
                      "status": "hypothesis", "prevalence": None,
                      "crowdedness": None, "constraint_class": "layer",
                      "tk_years": None, "td_years": None,
                      "chain": lyr.get("chain"), "position": lyr.get("position"),
                      "constraint": (lyr.get("physicalConstraintDesc") or "")[:300],
                      "grade": "HYPOTHESIS", "provenance": "prophetmap v1.4.0",
                      "suppliers": sups,
                      "crowdedness": prev.get("crowdedness"),
                      "evidence": prev.get("evidence", [])})
    g["nodes"] = nodes
    GRAPH.write_text(json.dumps(g, indent=1))
    # skeleton edges along chain position order (quarantine)
    def _chain(letter, lo, hi):
        return sorted([l for l in ls if l.get("chain") == letter
                       and lo <= (l.get("position") or 999) <= hi],
                      key=lambda l: l.get("position", 0))
    prod = {(e.get("source"), e.get("target"), e.get("relation"))
            for e in g.get("edges", [])}
    n_edge = 0
    for seq in (_chain("A", 0, 10), _chain("B", 11, 14)):
        for a, b in zip(seq, seq[1:]):
            if (f"PML_{a['id']}", f"PML_{b['id']}", "REQUIRES") in prod:
                continue
            e = E.blank_edge(f"PML_{a['id']}", f"PML_{b['id']}", "REQUIRES")
            e["note"] = ("skeleton: downstream layer requires upstream layer "
                         "(ProphetMap chain order — validate physically)")
            e = E.add_evidence(e, "adjacent layers in chain "
                                   f"{a.get('chain')} (positions "
                                   f"{a.get('position')}->{b.get('position')})",
                               "third_party/prophetmap/data/layers.json",
                               "2026-09-10", 0.3)
            E.propose(e)
            n_edge += 1
    return {"layers": len(ls), "tickers_linked": sum(len(v) for v in by_layer.values()),
            "nodes_total": len(nodes), "skeleton_edges": n_edge}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
