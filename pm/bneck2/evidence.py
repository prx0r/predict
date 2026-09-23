"""bneck evidence — three append-only tables (ProphetMap/Keystone/alphasig pattern).

kill_observations: verdict-logged falsifier checks, INCLUDING non-firings.
  {ts, node_id, signal, measured, threshold, verdict: TRIGGERED|NOT TRIGGERED|INCONCLUSIVE, source}
unknowns: Keystone-gaps-style ledger — missing evidence as checkable findings.
  {id, subject, sought, searched, would_close_it, status: open|closed, ts}
signals: alphasig-style ticker signals with decay handled at read time.
  {ts, ticker, type, direction: +1|-1|0, strength, confidence, source}

JSONL for logs (append = no rewrite races), JSON for the ledger. Stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BELIEFS = ROOT / "data" / "beliefs"
KILL_OBS = BELIEFS / "kill_observations.jsonl"
UNKNOWNS = BELIEFS / "unknowns.json"
SIGNALS = BELIEFS / "signals.jsonl"

VERDICTS = ("TRIGGERED", "NOT TRIGGERED", "INCONCLUSIVE")


def _append(path: Path, row: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def _read_log(path: Path) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []


def log_kill_observation(node_id: str, signal: str, measured: str, threshold: str,
                         verdict: str, source: str = "", ts: str = "") -> dict:
    assert verdict in VERDICTS, f"verdict must be one of {VERDICTS}"
    return _append(KILL_OBS, {"ts": ts, "node_id": node_id, "signal": signal,
                              "measured": measured, "threshold": threshold,
                              "verdict": verdict, "source": source})


def add_unknown(subject: str, sought: str, searched: str, would_close_it: str) -> dict:
    BELIEFS.mkdir(parents=True, exist_ok=True)
    try:
        ledger = json.loads(UNKNOWNS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ledger = {"unknowns": []}
    uid = f"u-{len(ledger['unknowns']) + 1:03d}"
    row = {"id": uid, "subject": subject, "sought": sought, "searched": searched,
           "would_close_it": would_close_it, "status": "open"}
    ledger["unknowns"].append(row)
    UNKNOWNS.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
    return row


def close_unknown(uid: str, how: str = "") -> bool:
    try:
        ledger = json.loads(UNKNOWNS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for row in ledger.get("unknowns", []):
        if row["id"] == uid and row["status"] == "open":
            row["status"] = "closed"
            row["closed_by"] = how
            UNKNOWNS.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
            return True
    return False


def log_signal(ticker: str, type: str, direction: int, strength: float,
               confidence: float, source: str = "", ts: str = "") -> dict:
    assert direction in (+1, -1, 0)
    return _append(SIGNALS, {"ts": ts, "ticker": ticker.upper(), "type": type,
                             "direction": direction,
                             "strength": round(float(strength), 3),
                             "confidence": round(float(confidence), 3),
                             "source": source})


def read_kill_observations(node_id: str = "") -> list[dict]:
    rows = _read_log(KILL_OBS)
    return [r for r in rows if not node_id or r.get("node_id") == node_id]


def read_unknowns(open_only: bool = True) -> list[dict]:
    try:
        ledger = json.loads(UNKNOWNS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = ledger.get("unknowns", [])
    return [r for r in rows if not open_only or r.get("status") == "open"]


def read_signals(ticker: str = "") -> list[dict]:
    rows = _read_log(SIGNALS)
    return [r for r in rows if not ticker or r.get("ticker") == ticker.upper()]
