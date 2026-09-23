"""bneck updater — Bayesian/temporal edge updater + exposure propagation.

The missing component (msg 18): belief signals -> edge weights -> tickers.

  fuse(prior, readings): log-odds pool over INDEPENDENT roots, prior as one
    pseudo-reading (weight 1). Transparent, no black box.
  update_edge(graph, edge_id, posterior, cause, ts): stamps the edge
    (confidence = posterior, valid_from = ts on regime change) and emits the
    11:42-UTC-style event record: p_before -> p_after, cause, pm delta,
    exposure gap, trigger state.
  downstream_tickers(graph, edge_id): tickers on nodes adjacent to the edge
    (losers if edge weakens, winners to re-derive via B(x) recursion).

Edges are matched by (source, target) or id. Stdlib only.
"""
from __future__ import annotations

import datetime
import math

MIN_P, MAX_P = 1e-6, 1 - 1e-6


def _clip(p: float) -> float:
    return max(MIN_P, min(MAX_P, float(p)))


def logit(p: float) -> float:
    p = _clip(p)
    return math.log(p / (1 - p))


def expit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def fuse(prior: float, readings: list[tuple[float, float]]) -> dict:
    """readings = [(p_i, weight_i)] — must already be lineage-collapsed
    (one entry per independent root; see belief.combine)."""
    num = logit(prior) * 1.0
    den = 1.0
    for p_i, w_i in readings:
        num += float(w_i) * logit(p_i)
        den += float(w_i)
    post = expit(num / den)
    return {"posterior": round(post, 3), "prior": round(_clip(prior), 3),
            "n_readings": len(readings)}


def update_edge(graph: dict, edge_id: tuple[str, str] | str, posterior: float,
                cause: str, ts: str = "", pm_before: float | None = None,
                pm_after: float | None = None) -> tuple[dict, dict]:
    """Stamp edge confidence; return (graph, event record)."""
    edge = None
    for e in graph.get("edges", []):
        key = (e.get("source"), e.get("target"))
        if key == edge_id or e.get("id") == edge_id:
            edge = e
            break
    if edge is None:
        raise KeyError(f"edge not found: {edge_id}")
    p_before = float(edge.get("confidence", 0.5))
    if isinstance(p_before, str):
        p_before = {"high": 0.8, "medium": 0.5, "low": 0.25}.get(p_before, 0.5)
    edge["confidence"] = round(posterior, 3)
    if abs(posterior - p_before) >= 0.15:
        edge["valid_from"] = ts or datetime.datetime.now(datetime.timezone.utc).isoformat()
    event = {
        "ts": ts or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "edge": [edge.get("source"), edge.get("target")],
        "p_before": round(p_before, 3), "p_after": round(posterior, 3),
        "delta": round(posterior - p_before, 3),
        "cause": cause,
        "pm_before": pm_before, "pm_after": pm_after,
        "pm_reprice": (round(pm_after - pm_before, 3)
                       if pm_before is not None and pm_after is not None else None),
        "kill_threshold": 0.5,
        "trigger": bool(posterior < 0.5 <= p_before),
    }
    return graph, event


def downstream_tickers(graph: dict, edge_id: tuple[str, str] | str) -> dict:
    """Tickers on nodes touching the edge + node labels for exposure notes."""
    target = None
    for e in graph.get("edges", []):
        if (e.get("source"), e.get("target")) == edge_id or e.get("id") == edge_id:
            target = (e.get("source"), e.get("target"))
            break
    if not target:
        return {"tickers": [], "nodes": []}
    touched = [n for n in graph.get("nodes", []) if n["id"] in target]
    tickers = sorted({t for n in touched for t in n.get("tickers", [])})
    return {"tickers": tickers, "nodes": [n["label"] for n in touched]}


def milestone_event(graph: dict, edge_id: tuple[str, str] | str, posterior: float,
                    milestone: str, evidence: str, ts: str = "") -> tuple[dict, dict]:
    """J_t jump wrapper: capability milestones reprice edge weights first,
    companies second. Cause is prefixed so event logs distinguish jumps
    (Navier-Stokes-class) from drift (quarterly data)."""
    cause = f"MILESTONE [{milestone}]: {evidence}"
    return update_edge(graph, edge_id, posterior, cause, ts)
