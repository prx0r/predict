"""Typed dependency edges — the primitive (graph reset P0).

An edge is the intellectual asset. Everything else is evidence about edges.
Unknowns are None, never 0.5. Tickers live on SUPPLIED_BY links, never on
physical nodes. Discovery writes HYPOTHESIS-grade candidates to quarantine;
validation promotes only with dated, sourced evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data" / "bottlenecks" / "graph_v2.json"
QUARANTINE = ROOT / "data" / "bottlenecks" / "graph_candidates.json"

GRADES = ("HYPOTHESIS", "SUPPORTED", "QUANTIFIED", "VALIDATED")
RELATIONS = ("REQUIRES", "CASCADE", "CATALYZES", "REGULATED_BY",
             "PATENT_COVERED_BY", "SUPPLIED_BY", "THREATENS")


def blank_edge(source: str, target: str, relation: str = "REQUIRES") -> dict:
    assert relation in RELATIONS, relation
    return {"source": source, "target": target, "relation": relation,
            "grade": "HYPOTHESIS", "valid_from": None, "valid_to": None,
            "confidence": "low",
            "requirement": {"quantity_per_unit": None, "unit": None,
                            "confidence": None},
            "supply": {"global_capacity": None, "utilization": None,
                       "lead_time_months": None, "capacity_growth_rate": None},
            "substitution": {"alternatives": [], "score": None},
            "timing": {"needed_by": None, "capacity_available_by": None},
            "evidence": []}


def add_evidence(edge: dict, value: str, source: str, date: str,
                 confidence: float) -> dict:
    edge = dict(edge)
    ev = list(edge.get("evidence", [])) + [{
        "value": value, "source": source, "date": date,
        "confidence": confidence}]
    edge["evidence"] = ev
    edge["grade"] = _grade(edge)
    edge["confidence"] = {"SUPPORTED": "medium", "QUANTIFIED": "high",
                          "VALIDATED": "high"}.get(edge["grade"], "low")
    return edge


def _grade(edge: dict) -> str:
    ev = edge.get("evidence", [])
    if not ev:
        return "HYPOTHESIS"
    req = edge.get("requirement", {})
    sup = edge.get("supply", {})
    sub = edge.get("substitution", {})
    quantified = (req.get("quantity_per_unit") is not None
                  or sup.get("utilization") is not None
                  or sup.get("lead_time_months") is not None
                  or sub.get("score") is not None)
    if len(ev) >= 2 and quantified:
        return "VALIDATED" if len(ev) >= 3 else "QUANTIFIED"
    return "SUPPORTED"


def propose(edge: dict) -> dict:
    """Discovery: quarantine a hypothesis-grade candidate, never production."""
    edge = dict(edge)
    edge["grade"] = _grade(edge)
    cands = []
    if QUARANTINE.exists():
        cands = json.loads(QUARANTINE.read_text())
    key = (edge["source"], edge["target"], edge["relation"])
    cands = [c for c in cands
             if (c["source"], c["target"], c["relation"]) != key]
    cands.append(edge)
    QUARANTINE.write_text(json.dumps(cands, indent=1))
    return {"quarantined": key, "candidates": len(cands)}


def promote(source: str, target: str, relation: str) -> dict:
    """Validation: move a candidate into production only with evidence."""
    if not QUARANTINE.exists():
        return {"error": "no quarantine"}
    cands = json.loads(QUARANTINE.read_text())
    match = [c for c in cands if (c["source"], c["target"], c["relation"])
             == (source, target, relation)]
    if not match:
        return {"error": "not found"}
    edge = match[0]
    if edge.get("grade", "HYPOTHESIS") == "HYPOTHESIS":
        return {"error": "no evidence — stays quarantined", "edge": edge}
    g = json.loads(GRAPH.read_text())
    edges = g.get("edges", [])
    edges = [e for e in edges if not (
        e.get("source") == source and e.get("target") == target
        and e.get("relation") == relation)]
    edges.append(edge)
    g["edges"] = edges
    GRAPH.write_text(json.dumps(g, indent=1))
    QUARANTINE.write_text(json.dumps(
        [c for c in cands if c is not match[0]], indent=1))
    return {"promoted": (source, target, relation), "grade": edge["grade"]}


def coverage() -> dict:
    """% of production edges with evidence / quantified fields."""
    g = json.loads(GRAPH.read_text())
    edges = g.get("edges", [])
    n = len(edges)
    if not n:
        return {"edges": 0}
    with_ev = sum(1 for e in edges if e.get("evidence") or e.get("evidence_url"))
    quant = sum(1 for e in edges
                if _has_number(e.get("requirement", {}))
                or _has_number(e.get("supply", {}))
                or _has_number(e.get("substitution", {}))
                or (e.get("substitutability") is not None)
                or (e.get("lead_time") is not None))
    return {"edges": n, "with_evidence": with_ev,
            "quantified": quant,
            "pct_evidence": round(with_ev / n, 3),
            "pct_quantified": round(quant / n, 3)}


def _has_number(d: dict) -> bool:
    return any(isinstance(v, (int, float)) for v in d.values())
