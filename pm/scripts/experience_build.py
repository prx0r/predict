#!/usr/bin/env python3
"""Rebuild derived experience store from canonical logs (cg Hydra idea).

data/experience.db is a PROJECTION: delete it any time, rebuild here,
byte-compare dumps to prove it. Nothing here is canonical; the JSONL
logs are. Usage: /usr/bin/python3 scripts/experience_build.py [--check]
--check exits nonzero if a rebuild differs (CI gate).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "experience.db"


def load_jsonl(path: Path) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []


def build(db_path: Path = DB) -> dict:
    from bneck2 import lab as LAB
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("CREATE TABLE receipts (hyp TEXT, verdict TEXT, n INT, ts TEXT)")
    cur.execute("CREATE TABLE verdicts (node TEXT, signal TEXT, verdict TEXT, ts TEXT)")
    cur.execute("CREATE TABLE panel (date TEXT, ticker TEXT, score REAL, fwd REAL)")
    cur.execute("CREATE TABLE severity (ts TEXT, node TEXT, b REAL)")
    counts = {}
    rows = LAB.load_receipts()
    cur.executemany("INSERT INTO receipts VALUES (?,?,?,?)",
                    [(r.get("hyp"), r.get("verdict"), r.get("n"), r.get("ts")) for r in rows])
    counts["receipts"] = len(rows)
    ver = load_jsonl(ROOT / "data" / "beliefs" / "kill_observations.jsonl")
    cur.executemany("INSERT INTO verdicts VALUES (?,?,?,?)",
                    [(r.get("node_id"), (r.get("signal") or "").split("(")[0],
                      r.get("verdict"), r.get("ts")) for r in ver])
    counts["verdicts"] = len(ver)
    from bneck2 import backtest as BT
    panel = BT.load_panel()
    cur.executemany("INSERT INTO panel VALUES (?,?,?,?)",
                    [(r.get("date"), r.get("ticker"), r.get("score"),
                      r.get("forward_return")) for r in panel])
    counts["panel"] = len(panel)
    sev = load_jsonl(ROOT / "data" / "bottlenecks" / "severity_history.jsonl")
    cur.executemany("INSERT INTO severity VALUES (?,?,?)",
                    [(r.get("ts"), r.get("node_id"), r.get("B")) for r in sev])
    counts["severity"] = len(sev)
    con.commit()
    dump = "\n".join(con.iterdump())
    con.close()
    counts["sha"] = hashlib.sha256(dump.encode()).hexdigest()[:16]
    return counts


def main() -> int:
    check = "--check" in sys.argv[1:]
    first = build()
    if not check:
        print(f"experience.db rebuilt: {first}")
        return 0
    second = build()
    if first == second:
        print(f"rebuild identical: {first}")
        return 0
    print(f"REBUILD DIFFERS: {first} vs {second}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
