"""Target workup — work a ticker backwards through the graph (stdlib).

Given a ticker: find its layer(s) -> walk REQUIRES edges upstream ->
surface constraints, researcher threats, crowdedness, moat, and LEADS
(next upstream exposures to investigate). Reads graph_v2, quarantine,
threats, crowded_longs, highlevel watchlist. Pure reads, JSON out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_all() -> dict:
    g = json.loads((ROOT / "data" / "bottlenecks" / "graph_v2.json").read_text())
    out = {"graph": g, "threats": {}, "crowded": {}, "watch": []}
    for name in ("threats.json", "crowded_longs.json", "threat_queue.json"):
        p = ROOT / "data" / "bottlenecks" / name
        if p.exists():
            out[name.split(".")[0]] = json.loads(p.read_text())
    try:
        q = ROOT / "data" / "bottlenecks" / "graph_candidates.json"
        out["quarantine"] = json.loads(q.read_text()) if q.exists() else []
    except OSError:
        out["quarantine"] = []
    try:
        out["highlevel"] = json.loads(
            (ROOT / "data" / "universe" / "highlevel_watchlist.json").read_text())
    except OSError:
        out["highlevel"] = {"candidates": []}
    return out


def layers_of(graph: dict, ticker: str) -> list[dict]:
    return [n for n in graph.get("nodes", [])
            if any(s.get("ticker") == ticker for s in n.get("suppliers", []))]


def upstream(graph: dict, start_ids: list[str], depth: int = 4) -> list[dict]:
    """Walk REQUIRES/DEPENDS_ON backwards: node -> what it needs."""
    by_src: dict[str, list] = {}
    for e in graph.get("edges", []):
        if e.get("relation") in ("REQUIRES", "DEPENDS_ON", "CASCADE"):
            by_src.setdefault(e["source"], []).append(e)
    seen, chain, frontier = set(start_ids), [], [(s, 0) for s in start_ids]
    while frontier:
        nid, d = frontier.pop(0)
        if d >= depth:
            continue
        for e in by_src.get(nid, []):
            t = e["target"]
            if t in seen:
                continue
            seen.add(t)
            chain.append({"from": nid, "needs": t,
                          "relation": e["relation"],
                          "grade": e.get("grade", "?"),
                          "depth": d + 1,
                          "supply": e.get("supply", {}),
                          "timing": e.get("timing", {})})
            frontier.append((t, d + 1))
    return chain


def workup(ticker: str) -> dict:
    d = load_all()
    g = d["graph"]
    layers = layers_of(g, ticker)
    names = {n["id"]: n for n in g["nodes"]}
    chains = upstream(g, [n["id"] for n in layers])
    # resolved upstream nodes with constraint info
    resolved = []
    for c in chains:
        n = names.get(c["needs"], {})
        resolved.append({**c,
                         "label": n.get("label", c["needs"]),
                         "crowdedness": n.get("crowdedness"),
                         "constraint": (n.get("constraint") or "")[:160]})
    threats = (d.get("threats") or {}).get(ticker, {})
    crowded = next((r for r in (d.get("crowded_longs") or {}).get("ranking", [])
                    if r["t"] == ticker), None)
    queue = next((r for r in (d.get("threat_queue") or {}).get("queue", [])
                  if r["ticker"] == ticker), None)
    hl = [c for c in (d.get("highlevel") or {}).get("candidates", [])
          if (c.get("ticker") or "").split(".")[0].split(":")[0] == ticker
          or ticker in (c.get("company") or "")]
    # leads: upstream nodes + quarantine edges touching the chain
    chain_ids = {c["needs"] for c in chains} | {n["id"] for n in layers}
    leads = []
    for q in d.get("quarantine", []):
        if q.get("source") in chain_ids or q.get("target") in chain_ids:
            leads.append(f"{q['source']} -{q['relation']}-> {q['target']}"
                         + (f" [{(q.get('note') or '')[:80]}]" if q.get("note") else ""))
    # critical analysis: bear/bull from evidence on hand
    bears, bulls = [], []
    for q in (threats.get("quotes") or []):
        bears.append(f"{q['by']}: {q['text'][:140]}")
    if threats.get("moat_flag"):
        bears.append(f"moat flag: {threats['moat_flag'][:140]}")
    for n in layers:
        for s in n.get("suppliers", []):
            if s.get("ticker") == ticker and s.get("ai_contribution"):
                bulls.append(f"ai_contribution {s['ai_contribution']} via {n['id']}")
    return {"ticker": ticker,
            "layers": [{"id": n["id"], "label": n.get("label"),
                        "crowdedness": n.get("crowdedness")} for n in layers],
            "reverse_chain": resolved,
            "threat": {"negatives": threats.get("negatives", 0),
                       "researchers": threats.get("researchers", [])},
            "crowded_rank": crowded,
            "triage": queue,
            "highlevel": [{"company": c.get("company"), "thesis": c.get("thesis"),
                           "status": c.get("status")} for c in hl],
            "leads": sorted(set(leads))[:15],
            "bear_case": bears[:5], "bull_case": bulls[:5],
            "verdict": ("OVERLOADED-LONG-AT-RISK" if crowded and threats.get("negatives")
                        else "THREATENED" if threats.get("negatives")
                        else "STRUCTURAL" if layers else "UNKNOWN")}


def main() -> dict:
    out = {}
    for t in sys.argv[1:] or ["LITE", "COHR", "MRVL"]:
        out[t] = workup(t)
        (ROOT / "data" / "bottlenecks" / f"workup_{t}.json").write_text(
            json.dumps(out[t], indent=1))
    return {"targets": list(out),
            "verdicts": {t: out[t]["verdict"] for t in out}}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
