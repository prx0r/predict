"""Headless MCP test — drives scripts/mcp_server.py over stdio JSON-RPC.

Spawns the server, runs initialize -> tools/list -> a battery of
tools/call (read-only only: no live collection, no writes), asserts
shapes. This is how every site feature gets tested headlessly.
Usage: /usr/bin/python3 scripts/mcp_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILED = []
# NOTE: standalone runs append one real E006 receipt + run file (it IS a
# real experiment run). The in-suite wrapper restores the logs; standalone
# runs intentionally leave the trail.


def check(name: str, cond: bool, detail: str = ""):
    print(("PASS " if cond else "FAIL ") + name, detail[:100])
    if not cond:
        FAILED.append(name)


class MCP:
    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "mcp_server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            cwd=str(ROOT))
        self._id = 0

    def call(self, method: str, params: dict | None = None,
             timeout: int = 120):
        self._id += 1
        self.proc.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": self._id, "method": method,
             "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line)

    def tool(self, name: str, args: dict | None = None):
        r = self.call("tools/call", {"name": name, "arguments": args or {}})
        if "error" in r:
            return {"_error": r["error"].get("message", "")[:200]}
        return {"_text": r["result"]["content"][0]["text"]}

    def close(self):
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        self.proc.wait(timeout=10)


def main() -> int:
    m = MCP()
    try:
        r = m.call("initialize", {"protocolVersion": "2024-11-05",
                                  "capabilities": {},
                                  "clientInfo": {"name": "t", "version": "0"}})
        check("initialize", r.get("result", {}).get("serverInfo", {}).get("name") == "bneck2")
        r = m.call("tools/list")
        tools = {t["name"] for t in r["result"]["tools"]}
        for need in ("status_board", "quant_board", "belief_board", "killfeed",
                     "migration_board", "signals_board", "experiment_run",
                     "experiment_report", "backtest", "threads_check",
                     "repo_state", "verdict_coverage", "scarcity_scan"):
            check(f"tool:{need}", need in tools)

        t = m.tool("status_board")["_text"]
        check("status_board content", "BINDING" in t or "binding" in t.lower(), t[:60])
        t = m.tool("quant_board")["_text"]
        check("quant_board content", "OVERWEIGHT" in t or "HOLD" in t or "WATCH" in t, t[:60])
        t = m.tool("belief_board")["_text"]
        check("belief_board content", "Belief board" in t, t[:60])
        t = m.tool("killfeed", {"live": False})["_text"]
        check("killfeed offline", "nodes=" in t, t[:80])
        t = m.tool("migration_board")["_text"]
        check("migration_board content", "dB/dt" in t, t[:60])
        t = m.tool("signals_board")["_text"]
        check("signals_board content", len(t) > 20, t[:60])
        t = m.tool("experiment_run", {"id": "E006"})["_text"]
        check("experiment_run E006", t.startswith("E006:"), t[:80])
        t = m.tool("experiment_run", {"id": "NOPE"})["_text"]
        check("experiment_run unknown", "unknown experiment" in t, t[:60])
        t = m.tool("experiment_report")["_text"]
        check("experiment_report content", "receipts=" in t, t[:60])
        t = m.tool("backtest")["_text"]
        check("backtest status", '"status"' in t, t[:80])
        t = m.tool("threads_check")["_text"]
        check("threads_check json", "unknowns_open" in t, t[:80])
        t = m.tool("repo_state")["_text"]
        check("repo_state count", "collectable:" in t, t[:60])
        t = m.tool("verdict_coverage")["_text"]
        check("verdict_coverage json", "cells_tested" in t, t[:60])
        t = m.tool("scarcity_scan", {"text": "cryogenic wafer probing"})["_text"]
        check("scarcity_scan tickers", "FORM" in t, t[:120])
        t = m.tool("target_workup", {"ticker": "COHR"})["_text"]
        check("target_workup content", "COHR" in t and "leads:" in t, t[:60])
        r = m.call("tools/call", {"name": "does_not_exist"})
        check("unknown tool errors", "error" in r)
        r = m.call("bogus/method")
        check("unknown method errors", "error" in r)
    finally:
        m.close()
    print(f"{len(FAILED)} failures")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
