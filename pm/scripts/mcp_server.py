"""bneck2 MCP server — stdlib-only Model Context Protocol over stdio.

Exposes the engine as MCP tools so agents (and our own headless tests)
can drive every site feature: boards, killfeed, experiments, backtest,
signals, ledger, predictions, threads, repo state. No third-party deps:
JSON-RPC 2.0 framing, newline-delimited, hand-rolled per the MCP spec
subset (initialize / tools/list / tools/call).

Usage: /usr/bin/python3 scripts/mcp_server.py   (speaks on stdin/stdout)
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _text(s: str) -> dict:
    return {"content": [{"type": "text", "text": s}]}


def t_status_board(args: dict) -> str:
    from bneck2 import graph as G
    from bneck2 import prices as P
    g = G.load_graph()
    tickers = sorted({t for n in g["nodes"] for t in n.get("tickers", [])})
    moves = P.get_moves(tickers)
    return G.render(g, moves, {}, {})


def t_quant_board(args: dict) -> str:
    from bneck2 import graph as G
    from bneck2 import quant as Q
    g = G.load_graph()
    rows = Q.score_all(g, Q.load_readings())
    crit = G.criticality(g)
    lines = []
    for r in rows:
        lines.append(f"{r['regime']:17} b={r['binding']:.2f} d={r['dissolution']:.2f} "
                     f"crit={crit.get(r['id'], 0):.2f} {r['label'][:44]}")
    return "\n".join(lines)


def t_belief_board(args: dict) -> str:
    import sys as _s
    _s.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "status_mod", str(ROOT / "scripts" / "status.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.belief_board(ROOT)


def t_killfeed(args: dict) -> str:
    from bneck2 import killfeed as K
    s = K.run(live=bool(args.get("live", False)),
              write=bool(args.get("write", False)),
              max_nodes=int(args.get("max_nodes", 0) or 0))
    return K.render_summary(s)


def t_migration_board(args: dict) -> str:
    from bneck2 import consistency as CY
    from bneck2 import graph as G
    from bneck2 import migration as M
    from bneck2 import quant as Q
    from bneck2 import worlds as W
    g = G.load_graph()
    readings = Q.load_readings()
    rows = Q.score_all(g, readings)
    hist = M.load_history()
    lines = []
    for r in rows:
        node = next(n for n in g["nodes"] if n["id"] == r["id"])
        sev = M.severity(node, readings.get(r["id"]))
        vel = M.velocity(r["id"], hist)
        lines.append(f"dB/dt={vel['dB_dt']:+.3f} B={sev['B']:.3f} {r['id']}")
    doc = W.load_worlds()
    lines.append("")
    lines.append(CY.render(CY.find_inconsistencies(doc)))
    return "\n".join(lines)


def t_signals_board(args: dict) -> str:
    from bneck2 import predict as PD
    files = sorted((ROOT / "data" / "predict").glob("panel-*.jsonl"))
    rows = []
    for f in files:
        rows += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    if not rows:
        return "no monthly panel; run scripts/build_predict_panel.py"
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 3, 0)]
    train = [r for r in rows if r["date"] < cut]
    cur = [r for r in rows if r["date"] == dates[-1]]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 20]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    scored = PD.composite_by_date(cur, winners or ["f_mom_20"], signs)
    return "\n".join(f"{r['score']:+.3f} {r['ticker']:9}"
                     for r in sorted(scored, key=lambda x: -x["score"]))


def t_target_workup(args: dict) -> str:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "workup_mod", str(ROOT / "scripts" / "work_target.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tick = str(args.get("ticker", "LITE")).upper()
    w = mod.workup(tick)
    lines = [f"{tick} verdict={w['verdict']}",
             f"layers={[(l['id'], l['crowdedness']) for l in w['layers']]}",
             "reverse-chain:"]
    for c in w["reverse_chain"][:8]:
        lines.append(f"  {c['from']} -{c['relation']}-> {c['needs']} "
                     f"[{c['grade']}] {c.get('label', '')[:40]}")
    lines.append(f"threats={w['threat']} triage={w['triage']}")
    lines.append("leads:")
    for lead in w["leads"][:10]:
        lines.append(f"  + {lead[:100]}")
    lines.append(f"bear={w['bear_case'][:2]}")
    return "\n".join(lines)


def t_experiment_run(args: dict) -> str:
    from bneck2 import experiments as X
    from bneck2 import lab as LAB
    hid = str(args.get("id", ""))
    fn = X.REGISTRY.get(hid)
    if not fn:
        return f"unknown experiment (have: {', '.join(sorted(X.REGISTRY))})"
    try:
        result, verdict, n = fn()
    except Exception as exc:
        result, verdict, n = {"error": str(exc)[:200]}, "INCONCLUSIVE", 0
    LAB.receipt(hid, result, verdict, n,
                comparisons=int(result.get("comparisons", 1)))
    return f"{hid}: {verdict} n={n} :: {json.dumps(result)[:800]}"


def t_experiment_report(args: dict) -> str:
    from bneck2 import lab as LAB
    return LAB.report()


def t_backtest(args: dict) -> str:
    from bneck2 import backtest as BT
    return json.dumps(BT.live_result(), indent=1)


def t_threads_check(args: dict) -> str:
    from bneck2 import evidence as E
    from bneck2 import lab as LAB
    hyps = {}
    for r in LAB.load_receipts():
        hyps[r.get("hyp", "?")] = r.get("verdict", "INCONCLUSIVE")
    return json.dumps({
        "unknowns_open": len(E.read_unknowns()),
        "hyps_open": sum(1 for v in hyps.values() if v == "INCONCLUSIVE"),
        "preds_open": sum(1 for r in LAB.load_predictions()
                          if r.get("resolved") is None)}, indent=1)


def t_repo_state(args: dict) -> str:
    import unittest
    loader = unittest.TestLoader()
    n = loader.discover(str(ROOT / "tests")).countTestCases()
    return f"tests collectable: {n}"


def t_verdict_coverage(args: dict) -> str:
    from bneck2 import lab as LAB
    return json.dumps(LAB.verdict_coverage(), indent=1)


def t_scarcity_scan(args: dict) -> str:
    from bneck2 import scarcity as SC
    return json.dumps(SC.scan_text(str(args.get("text", ""))), indent=1)


TOOLS = {
    "status_board": (t_status_board, "Ranked bottleneck board (prices + conviction).", {}),
    "quant_board": (t_quant_board, "Regimes, Tk/Td, redundancy, convexity, criticality.", {}),
    "belief_board": (t_belief_board, "Clock-disagreement board from claims.json.", {}),
    "killfeed": (t_killfeed, "Collect->evaluate->verdict loop.",
                 {"live": False, "write": False, "max_nodes": 0}),
    "migration_board": (t_migration_board, "Severity/velocity/X/derivatives/consistency.", {}),
    "signals_board": (t_signals_board, "Composite scores with evidence bounds.", {}),
    "experiment_run": (t_experiment_run, "Run one experiment by id (E001..); logs receipt.",
                       {"id": "E006"}),
    "experiment_report": (t_experiment_report, "Ledger report rebuilt from receipts.", {}),
    "backtest": (t_backtest, "Walk-forward status (OK/INSUFFICIENT/BLOCKED).", {}),
    "threads_check": (t_threads_check, "Live open-thread counts.", {}),
    "repo_state": (t_repo_state, "Test counts + tree sanity.", {}),
    "verdict_coverage": (t_verdict_coverage, "Cells tested vs triggered.", {}),
    "scarcity_scan": (t_scarcity_scan, "Breakthrough text -> nodes + tickers.",
                      {"text": "cryogenic wafer probing"}),
}
TOOLS["target_workup"] = (
    t_target_workup, "Reverse-chain workup: ticker -> layers -> upstream leads.",
    {"ticker": "LITE"})


def handle(msg: dict):
    mid = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {}) or {}

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({"protocolVersion": "2024-11-05",
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "bneck2", "version": "0.3.0"}})
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return ok({"tools": [
            {"name": name,
             "description": fn.__doc__ or desc,
             "inputSchema": {"type": "object",
                             "properties": {k: {"type": "string"}
                                            for k in defaults},
                             "additionalProperties": True}}
            for name, (fn, desc, defaults) in TOOLS.items()]})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        if name not in TOOLS:
            return err(-32602, f"unknown tool: {name}")
        fn, _, _ = TOOLS[name]
        try:
            return ok(_text(fn(args)))
        except Exception:
            return err(-32603, traceback.format_exc(limit=3)[-800:])
    if method == "ping":
        return ok({})
    return err(-32601, f"unknown method: {method}")


def main() -> int:
    inp, out = sys.stdin, sys.stdout
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            resp = handle(msg)
        except Exception:
            resp = {"jsonrpc": "2.0", "id": msg.get("id"),
                    "error": {"code": -32603, "message": "handler crashed"}}
        if resp is not None:
            out.write(json.dumps(resp) + "\n")
            out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
