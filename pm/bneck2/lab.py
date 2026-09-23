"""bneck2 lab — cg-flow experimentation loop (see third_party/cg SPEC/AGENTS).

Flow (formalized from cogymkernel, adapted to evidence work):
  HYPOTHESIZE -> PREREGISTER -> RUN -> RECEIPT -> VERDICT -> NEXT

Rules borrowed verbatim in spirit:
- Receipts (JSONL) are canonical. Projections (reports) rebuild from them;
  deleting a projection destroys no evidence (cg §56 idea).
- Gates dominate objectives: a hypothesis needs a FALSIFIER up front, or
  it is not a hypothesis — it's a vibe. Vibes go in notes/, never verdicts.
- PILOT honesty: n<30 decisions => directional only, labelled everywhere.
- Determinism: receipts carry input hashes; same inputs => same verdict.
- LLM judgment never enters a verdict. It may propose hypotheses; only
  measured data disposes them.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "experimentation"
HYPS = LAB / "hypotheses"
RECEIPTS = LAB / "receipts.jsonl"
RUNS = LAB / "runs"
CACHE = ROOT / "data" / "cache"

VERDICTS = ("CONFIRMED", "REFUTED", "INCONCLUSIVE",
            "PROVISIONAL", "DISPUTED", "BLOCKED", "EXPLORATORY")
# Lifecycle (peer-review P1 fix): DISCOVERY search results are EXPLORATORY
# by construction — they may seed preregistrations but never count as
# confirmation, however strong the selected statistic looks. Preregistered
# tests on untouched data earn CONFIRMED/REFUTED. Every mutation gets a new
# hypothesis ID (HEP rule).


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def preregister(hyp_id: str, title: str, prediction: str, falsifier: str,
                data: str = "", status: str = "open") -> Path:
    """Write the hypothesis file if absent; never overwrite (append-only)."""
    HYPS.mkdir(parents=True, exist_ok=True)
    path = HYPS / f"{hyp_id}.md"
    if not path.exists():
        path.write_text(
            f"# {hyp_id}: {title}\n\n"
            f"- status: {status}\n"
            f"- prediction: {prediction}\n"
            f"- falsifier: {falsifier}\n"
            f"- data: {data}\n",
            encoding="utf-8")
    return path


def receipt(hyp_id: str, result: dict, verdict: str, n: int,
            ts: str = "", comparisons: int = 1) -> dict:
    """comparisons = number of configurations searched to produce this
    result (lags, thresholds, subsets). Uncorrected search inflates
    significance: receipts with comparisons>1 are flagged and can only
    carry EXPLORATORY, never CONFIRMED."""
    assert verdict in VERDICTS, f"verdict must be one of {VERDICTS}"
    if comparisons > 1 and verdict == "CONFIRMED":
        raise ValueError(
            f"comparisons={comparisons} without correction cannot CONFIRM; "
            f"use EXPLORATORY and preregister a holdout test")
    blob = json.dumps(result, sort_keys=True, default=str)
    row = {"ts": ts or utcnow(), "hyp": hyp_id,
           "inputs_hash": hashlib.sha256(blob.encode()).hexdigest()[:16],
           "n": n, "verdict": verdict, "comparisons": comparisons,
           "directional_only": n < 30,
           "result": result}
    LAB.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load_receipts(hyp_id: str = "") -> list[dict]:
    try:
        rows = [json.loads(l) for l in RECEIPTS.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []
    return [r for r in rows if not hyp_id or r.get("hyp") == hyp_id]


def report() -> str:
    """Projection rebuilt purely from receipts (delete-safe)."""
    rows = load_receipts()
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r.get("hyp", "?"), []).append(r)
    lines = ["# Experiment report — rebuilt from receipts",
             f"receipts={len(rows)} hypotheses={len(by)}"]
    for hyp, rs in sorted(by.items()):
        last = rs[-1]
        flag = " (directional-only)" if last.get("directional_only") else ""
        comp = last.get("comparisons", 1)
        if comp > 1:
            flag += f" [searched {comp} configs]"
        lines.append(f"\n## {hyp}: {last['verdict']}{flag} "
                     f"(n={last.get('n')}, runs={len(rs)})")
        res = last.get("result", {})
        note = res.get("note") or res.get("summary") or ""
        if note:
            lines.append(f"   {str(note)[:300]}")
    return "\n".join(lines)


import math


def wilson(hits: int, n: int, z: float = 1.96) -> dict:
    """Wilson 95% interval for small-n hit rates (honest uncertainty)."""
    if n <= 0:
        return {"rate": 0.0, "lo": 0.0, "hi": 1.0, "n": 0}
    ph = hits / n
    den = 1 + z * z / n
    c = ph + z * z / (2 * n)
    m = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return {"rate": round(ph, 3), "lo": round(max((c - m) / den, 0.0), 3),
            "hi": round(min((c + m) / den, 1.0), 3), "n": n}


def support_rate(rows: list[dict] | None = None) -> dict:
    """DiscoPER metric: fraction of disposed hypotheses CONFIRMED."""
    rows = rows if rows is not None else load_receipts()
    decided = [r for r in rows if r.get("verdict") in ("CONFIRMED", "REFUTED")]
    hits = sum(1 for r in decided if r["verdict"] == "CONFIRMED")
    w = wilson(hits, len(decided))
    w["decided"] = len(decided)
    w["open"] = sum(1 for r in rows if r.get("verdict") in
                    ("INCONCLUSIVE", "PROVISIONAL", "DISPUTED", "EXPLORATORY"))
    w["blocked"] = sum(1 for r in rows if r.get("verdict") == "BLOCKED")
    return w


def possibility_ledger(rows: list[dict] | None = None) -> dict:
    """Quantitative space accounting: what the logs have ruled in/out.

    Space = (node x leg x window) verdict cells + hypothesis verdicts.
    INCONCLUSIVE never counts as elimination (anti-hope rule).
    """
    rows = rows if rows is not None else load_receipts()
    by_hyp: dict[str, str] = {}
    for r in rows:
        by_hyp[r.get("hyp", "?")] = r.get("verdict", "INCONCLUSIVE")
    return {"hypotheses": len(by_hyp),
            "confirmed": sum(1 for v in by_hyp.values() if v == "CONFIRMED"),
            "refuted": sum(1 for v in by_hyp.values() if v == "REFUTED"),
            "open": sum(1 for v in by_hyp.values() if v in
                        ("INCONCLUSIVE", "PROVISIONAL", "DISPUTED",
                         "EXPLORATORY")),
            "runs": len(rows)}


def verdict_coverage(root=None) -> dict:
    """(node, leg) cells ever TRIGGERED vs ever tested (local logs)."""
    import json as _j
    base = Path(root) if root else ROOT
    try:
        ver = [_j.loads(l) for l in
               (base / "data" / "beliefs" / "kill_observations.jsonl")
               .read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return {"cells_tested": 0, "cells_triggered": 0, "rows": 0}
    tested = {(r.get("node_id"), (r.get("signal") or "").split("(")[0])
              for r in ver}
    trig = {(r.get("node_id"), (r.get("signal") or "").split("(")[0])
            for r in ver if r.get("verdict") == "TRIGGERED"}
    return {"cells_tested": len(tested), "cells_triggered": len(trig),
            "rows": len(ver),
            "triggered_cells": sorted(f"{a}:{b}" for a, b in trig)}


PREDICTIONS = LAB / "predictions.jsonl"


def predict(var: str, target: str, direction: int, resolve_after: str,
            note: str = "") -> dict:
    """Preregister a directional prediction (resolve_after YYYY-MM-DD)."""
    assert direction in (+1, -1)
    LAB.mkdir(parents=True, exist_ok=True)
    row = {"var": var, "target": target, "direction": direction,
           "resolve_after": resolve_after, "resolved": None, "note": note}
    with open(PREDICTIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load_predictions() -> list[dict]:
    try:
        return [json.loads(l) for l in PREDICTIONS.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []


def resolve_due(resolver) -> list[dict]:
    """Resolve due predictions via resolver(row)->+1|-1|None. Rewrites file."""
    rows = load_predictions()
    today = utcnow()[:10]
    n = 0
    for r in rows:
        if r.get("resolved") is None and r.get("resolve_after", "") <= today:
            out = resolver(r)
            if out in (+1, -1):
                r["resolved"] = out
                r["hit"] = out == r["direction"]
                n += 1
    PREDICTIONS.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                           encoding="utf-8")
    return [r for r in rows if r.get("resolved") is not None][-n:] if n else []


def run_file(hyp_id: str, inputs: dict, outputs: dict, ts: str = "",
             code_refs: dict | None = None) -> Path:
    """Immutable per-run file (cg RunReceipt idea): full inputs+outputs.
    Receipt row indexes it. Volatile fields (ts) live beside the id."""
    RUNS.mkdir(parents=True, exist_ok=True)
    ts = ts or utcnow()
    blob = json.dumps(inputs, sort_keys=True, default=str)
    rid = hashlib.sha256(blob.encode()).hexdigest()[:12]
    path = RUNS / f"{hyp_id}-{ts.replace(':', '')}-{rid}.json"
    path.write_text(json.dumps({"hyp": hyp_id, "ts": ts,
                                "inputs_hash": rid, "inputs": inputs,
                                "outputs": outputs,
                                "code_refs": code_refs or {}}, indent=1),
                    encoding="utf-8")
    return path


def cache_get(key: str):
    try:
        return json.loads((CACHE / (key + ".json")).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def cache_set(key: str, value) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / (key + ".json")).write_text(json.dumps(value), encoding="utf-8")


def cache_key(*parts: str) -> str:
    blob = "|".join(parts)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


ALOG = LAB / "a-logs"


def alog(task: str, detail: str, ts: str = "") -> dict:
    """Append-only agent progress log (A-tasks). One line per action."""
    ALOG.mkdir(parents=True, exist_ok=True)
    row = {"ts": ts or utcnow(), "task": task, "detail": detail[:500]}
    import json as _j
    with open(ALOG / "a-log.jsonl", "a", encoding="utf-8") as f:
        f.write(_j.dumps(row) + "\n")
    return row
