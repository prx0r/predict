"""Stdlib shock propagation over the dependency graph (kernel port).

Port of imported/postagi_kernel WorldGraph.propagate (needs networkx):
shock * elasticity * confidence * damping * delay-weight, summed over
paths in topological order. Edges carry no elasticity yet -> defaults:
REQUIRES 0.8, CASCADE 0.6, CATALYZES 0.5, others 0.3; confidence from
grade (VALIDATED 0.9 / QUANTIFIED 0.7 / SUPPORTED 0.5 / HYPOTHESIS 0.3);
delay from supply.lead_time_months (/12, capped by horizon).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data" / "bottlenecks" / "graph_v2.json"

ELAST = {"REQUIRES": 0.8, "CASCADE": 0.6, "CATALYZES": 0.5,
         "REGULATED_BY": 0.3, "PATENT_COVERED_BY": 0.3,
         "SUPPLIED_BY": 0.4, "THREATENS": -0.5, "DEPENDS_ON": 0.8}
GRADE_CONF = {"VALIDATED": 0.9, "QUANTIFIED": 0.7, "SUPPORTED": 0.5,
              "HYPOTHESIS": 0.3}


def _params(edge: dict) -> tuple[float, float, float]:
    elast = ELAST.get(edge.get("relation", ""), 0.3)
    conf = GRADE_CONF.get(edge.get("grade") or _legacy_conf(edge), 0.3)
    lt = (edge.get("supply") or {}).get("lead_time_months")
    delay = (lt / 12.0) if isinstance(lt, (int, float)) else 0.0
    return elast, conf, delay


def _legacy_conf(edge: dict) -> str:
    return {"high": "QUANTIFIED", "medium": "SUPPORTED"}.get(
        edge.get("confidence", ""), "HYPOTHESIS")


def topo(nodes: list[str], edges: list[dict]) -> list[str]:
    deps = {n: set() for n in nodes}
    for e in edges:
        if e.get("source") in deps and e.get("target") in deps:
            deps[e["target"]].add(e["source"])
    order, ready = [], sorted(n for n, d in deps.items() if not d)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m, d in deps.items():
            if n in d:
                d.discard(n)
                if not d and m not in order and m not in ready:
                    ready.append(m)
        ready.sort()
    return order + sorted(set(nodes) - set(order))


def propagate(graph: dict, shocks: dict[str, float],
              horizon_years: float = 5.0, damping: float = 0.92) -> dict:
    nodes = [n["id"] for n in graph.get("nodes", [])]
    edges = graph.get("edges", [])
    state = {n: 0.0 for n in nodes}
    for n, v in shocks.items():
        if n in state:
            state[n] += float(v)
    out = {e["source"]: [] for e in edges}
    for e in edges:
        out.setdefault(e.get("source"), []).append(e)
    for src in topo(nodes, edges):
        for e in out.get(src, []):
            dst = e.get("target")
            if dst not in state:
                continue
            elast, conf, delay = _params(e)
            if delay > horizon_years:
                continue
            tw = max(0.0, 1.0 - delay / max(horizon_years, 1e-9))
            state[dst] += state[src] * elast * conf * damping * tw
    return {k: round(v, 4) for k, v in state.items()}


def bottleneck_rank(state: dict, graph: dict, top: int = 10) -> list:
    names = {n["id"]: n.get("label", n["id"]) for n in graph.get("nodes", [])}
    return [(nid, names.get(nid, nid), v)
            for nid, v in sorted(state.items(), key=lambda x: -abs(x[1]))[:top]]


def with_threats() -> dict:
    """Production graph + THREATENS overlay merged (overlay wins ties)."""
    graph = json.loads(GRAPH.read_text())
    nodes = {n["id"]: dict(n) for n in graph.get("nodes", [])}
    edges = list(graph.get("edges", []))
    try:
        ov = json.loads((ROOT / "data" / "bottlenecks" / "threat_graph.json").read_text())
        for n in ov.get("nodes", []):
            nodes.setdefault(n["id"], n)
        edges += ov.get("edges", [])
    except OSError:
        pass
    return {"nodes": list(nodes.values()), "edges": edges}


def death_watch(shock_node: str = "PML_L0", shock: float = 1.0,
                top: int = 15) -> dict:
    """Shock an AI capability -> threatened companies ranked by exposure."""
    import re as _re
    graph = with_threats()
    state = propagate(graph, {shock_node: shock})
    co = [(nid, v) for nid, v in state.items() if nid.startswith("CO_")]
    depth = {}
    try:
        _ov = json.loads((ROOT / "data" / "bottlenecks" / "threat_graph.json").read_text())
        for e in _ov.get("edges", []):
            by = {q.get("source", "") for q in e.get("evidence", [])}
            depth[e["target"]] = (len(e.get("evidence", [])), len(by))
    except OSError:
        pass
    co.sort(key=lambda x: (-abs(x[1]), -depth.get(x[0], (0, 0))[0],
                           -depth.get(x[0], (0, 0))[1]))
    names = {n["id"]: n.get("label", n["id"]) for n in graph["nodes"]}
    ev = {}
    try:
        ov = json.loads((ROOT / "data" / "bottlenecks" / "threat_graph.json").read_text())
        for e in ov.get("edges", []):
            ev[e["target"]] = [q.get("source", "").replace("feedify:", "")
                               for q in e.get("evidence", [])[:2]]
    except OSError:
        pass
    return {"shock": {shock_node: shock},
            "watch": [{"ticker": _re.sub(r"^CO_", "", nid), "exposure": v,
                       "by": ev.get(nid, [])} for nid, v in co[:top] if abs(v) > 0.0005]}


def main() -> dict:
    graph = json.loads(GRAPH.read_text())
    shocks = {"PML_L2": 1.0}  # +1 training-compute demand shock
    state = propagate(graph, shocks)
    return {"shock": shocks,
            "top": bottleneck_rank(state, graph, 12)}
