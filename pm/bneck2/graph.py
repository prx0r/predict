"""bneck graph — bottleneck nodes, temporal edges, conviction + short board.

Node (v2 schema): id, label, type, branch, status, prevalence, crowdedness,
  tickers[], relieved_by[], kill_signals[], precedents[],
  constraint_class, eliminability, tk_years, td_years, min_latency_years,
  destroy_paths[], constrain_paths[],
  agi_p, deploy_p, revenue_purity, op_leverage, expect_years (short math).

Edge: source, target, relation, amount, capacity, utilization, lead_time,
  substitutability, valid_from, valid_to, confidence, evidence_url.

conviction = 0.5*prevalence + 0.3*(1-crowdedness) + 0.2*evidence_norm.
short_score = crowdedness * (0.3 + 0.7*kill_ratio), binding nodes only.

Stdlib only. Pure functions.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "data" / "bottlenecks" / "graph_v2.json"

STATUS_ORDER = {"binding": 0, "emerging": 1, "latent": 2, "solved": 3}


def load_graph(path: Path = GRAPH_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def score_node(node: dict) -> float:
    prevalence = float(node.get("prevalence") if node.get("prevalence") is not None else 0.5)
    crowdedness = float(node.get("crowdedness") if node.get("crowdedness") is not None else 0.5)
    evidence = min(1.0, len(node.get("evidence", [])) / 5.0)
    return round(0.5 * prevalence + 0.3 * (1 - crowdedness) + 0.2 * evidence, 3)


def rank(graph: dict) -> list[tuple[float, dict]]:
    scored = [(score_node(n), n) for n in graph.get("nodes", [])]
    scored.sort(key=lambda t: (STATUS_ORDER.get(t[1].get("status", "latent"), 9), -t[0]))
    return scored


def rebalance_action(node: dict, score: float) -> str:
    status = node.get("status", "latent")
    crowded = float(node.get("crowdedness") if node.get("crowdedness") is not None else 0.5)
    if status == "solved":
        return "EXIT — thesis played out or dissolved"
    if status == "binding" and crowded < 0.5 and score >= 0.55:
        return "OVERWEIGHT — binding and not yet crowded"
    if status == "binding":
        return "HOLD — owns the bottleneck; doubles as regime indicator"
    if status == "emerging" and score >= 0.5 and crowded < 0.5:
        return "ACCUMULATE — n+1 candidate, scale on confirmation"
    if status == "emerging":
        return "WATCH — track kill/confirm signals"
    return "IGNORE — latent"


def short_score(node: dict, triggered: list[str] | None = None) -> float:
    """The digger trade: crowded picks-and-shovels at dissolution."""
    if node.get("status") != "binding":
        return 0.0
    kills = node.get("kill_signals", [])
    trig = set(triggered or [])
    ratio = (sum(1 for k in kills if k in trig) / len(kills)) if kills else 0.0
    return round(float(node.get("crowdedness") if node.get("crowdedness") is not None else 0.5) * (0.3 + 0.7 * ratio), 3)


def short_action(node: dict, sscore: float, triggered: list[str] | None = None) -> str:
    if node.get("status") != "binding":
        return ""
    if triggered:
        return "SHORT WATCH — crowded long + kill confirmed; define risk (puts/spreads), pair vs the dissolver"
    if sscore >= 0.2:
        return "DISSOLUTION WATCH — crowded; size any short only on kill trigger"
    return ""


def check_kill_signals(node: dict, triggered: list[str] | None = None) -> list[str]:
    trig = set(triggered or [])
    return [f"{s}{' [TRIGGERED]' if s in trig else ''}" for s in node.get("kill_signals", [])]


def criticality(graph: dict) -> dict[str, float]:
    """N-1 removal score (CHOKEPOINT pattern, stdlib).

    criticality(v) = sum over dependents u of weight(u)/depth, where an
    edge source->target means source DEPENDS ON target (all our relations
    point at the constraint). Ticker-bearing nodes weight 1.0, others 0.5.
    Answers: whose removal breaks the most downstream value?
    """
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    dependents: dict[str, list[str]] = {}
    for e in graph.get("edges", []):
        s, t = e.get("source"), e.get("target")
        if s not in nodes or t not in nodes or s == t:
            continue
        # DEPENDS_ON/REGULATED_BY/PATENT_COVERED_BY: source needs target.
        # CASCADE: demand flows src->dst, so dst breaks if src breaks.
        if e.get("relation") == "CASCADE":
            dependents.setdefault(s, []).append(t)
        else:
            dependents.setdefault(t, []).append(s)
    scores: dict[str, float] = {}
    for vid in nodes:
        total, seen, frontier = 0.0, {vid}, [(d, 1) for d in dependents.get(vid, [])]
        while frontier:
            uid, depth = frontier.pop(0)
            if uid in seen:
                continue
            seen.add(uid)
            total += (1.0 if nodes[uid].get("tickers") else 0.5) / depth
            frontier.extend((d, depth + 1) for d in dependents.get(uid, []))
        scores[vid] = round(total, 3)
    return scores


def destroy_constrain(node: dict) -> list[str]:
    """The two opposing questions per economically valuable node."""
    out = []
    if node.get("destroy_paths"):
        out.append(f"DESTROY (what makes this unnecessary): {'; '.join(node['destroy_paths'])}")
    if node.get("constrain_paths"):
        out.append(f"CONSTRAIN (what still blocks scale if cognition were free): {'; '.join(node['constrain_paths'])}")
    return out


def tk_td_line(node: dict) -> str:
    tk, td = node.get("tk_years"), node.get("td_years")
    if tk is None or td is None:
        return ""
    sig = "LONG-WINDOW (Td<<Tk)" if td * 2 <= tk else ("CLOSING (Tk<=2)" if tk <= 2 else "MID")
    return f"Tk={tk}y kill / Td={td}y demand-overwhelm -> {sig}"


def dissolution_board(graph: dict, moves: dict | None = None,
                      triggered: dict[str, list[str]] | None = None,
                      convexity: dict[str, float] | None = None) -> str:
    moves = moves or {}
    triggered = triggered or {}
    convexity = convexity or {}
    rows = []
    for node in graph.get("nodes", []):
        if node.get("status") != "binding":
            continue
        trig = triggered.get(node["id"], [])
        rows.append((short_score(node, trig), node, trig))
    rows.sort(key=lambda t: -t[0])
    lines = ["# Dissolution board — short the shovels when the digger arrives"]
    for sscore, node, trig in rows:
        tickers = node.get("tickers", [])
        priced = " ".join(f"{t}{moves[t]['pct_1d']:+.1f}%" for t in tickers if t in moves) or "unpriced"
        conv = convexity.get(node["id"])
        conv_s = f" | ShortConvexity {conv:.2f}" if conv is not None else ""
        flag = "  !! TRIGGERED" if trig else ""
        lines.append(f"## {node['label']} (short {sscore:.2f}{conv_s}){flag}")
        lines.append(f"   crowded long: {' '.join(tickers) or '-'} | 1d: {priced}")
        lines.append(f"   digger: {', '.join(node.get('relieved_by', [])) or '?'}")
        if node.get("precedents"):
            lines.append(f"   rhymes with: {', '.join(node['precedents'])}")
        action = short_action(node, sscore, trig)
        if action:
            lines.append(f"   -> {action}")
        lines.append("")
    return "\n".join(lines)


def render(graph: dict, moves: dict | None = None,
           triggered: dict[str, list[str]] | None = None,
           convexity: dict[str, float] | None = None) -> str:
    moves = moves or {}
    triggered = triggered or {}
    lines = [f"# Bottleneck status — {graph.get('name', 'graph')}"]
    lines.append(f"Thesis: {graph.get('thesis', '')}\n")
    for score, node in rank(graph):
        tickers = node.get("tickers", [])
        priced = " ".join(f"{t}{moves[t]['pct_1d']:+.1f}%" for t in tickers if t in moves) or "unpriced"
        trig = triggered.get(node["id"], [])
        warn = "  !! KILL SIGNAL TRIGGERED" if trig else ""
        cls = node.get("constraint_class", "?")
        lines.append(f"## [{node.get('status', 'latent').upper()}] {node['label']} (conviction {score:.2f}){warn}")
        lines.append(f"   class: {cls} (eliminability {node.get('eliminability', '?')}) | tickers: {' '.join(tickers) or '-'} | 1d: {priced}")
        tkline = tk_td_line(node)
        if tkline:
            lines.append(f"   {tkline}")
        lines.append(f"   -> {rebalance_action(node, score)}")
        if node.get("relieved_by"):
            lines.append(f"   dissolved by: {', '.join(node['relieved_by'])}")
        for dc in destroy_constrain(node):
            lines.append(f"   {dc}")
        for sig in check_kill_signals(node, trig):
            lines.append(f"   kill-watch: {sig}")
        lines.append("")
    lines.append(dissolution_board(graph, moves, triggered, convexity))
    return "\n".join(lines)
