"""bneck diggers — experimental-substrate feed with a proof ladder.

A digger claim advances ONLY on evidence, rung by rung:
  L0 CLAIM          company says it works
  L1 SILICON        tapeout / working prototype
  L2 PEER_REVIEW    peer-reviewed results (Hot Chips, arXiv w/ artifact)
  L3 INDEPENDENT    third-party replication or benchmark
  L4 NORMALIZED     workload-normalized frontier comparison
                    (tokens/$, tokens/W, latency, yield, scale)
  L5 DEPLOYED       production scale

Normal CN101 sits at L2 (Hot Chips 2026 + arXiv 2608.00754): genuinely
interesting, not yet proof. Extropic Z1 at L1 (X0 proven, Z1 pre-prod).
Nothing advances without an evidence URL. Stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGGERS_PATH = ROOT / "data" / "labs" / "diggers.json"

RUNGS = ["CLAIM", "SILICON", "PEER_REVIEW", "INDEPENDENT", "NORMALIZED", "DEPLOYED"]


def load_diggers(path: Path = DIGGERS_PATH) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("diggers", [])
    except (OSError, ValueError):
        return []


def rung_index(rung: str) -> int:
    return RUNGS.index(rung) if rung in RUNGS else -1


def advance(digger: dict, rung: str, evidence_url: str) -> dict:
    """Move up the ladder only with evidence. Never skips, never downgrades."""
    if not evidence_url:
        raise ValueError("no evidence, no advance")
    new, cur = rung_index(rung), rung_index(digger.get("rung", "CLAIM"))
    if new < 0:
        raise ValueError(f"unknown rung: {rung}")
    if new == cur + 1:
        digger["rung"] = rung
        digger.setdefault("evidence", []).append({"rung": rung, "url": evidence_url})
    return digger


def substitution_ready(digger: dict) -> bool:
    """Only L4+ counts toward kill_signals / substitution_milestone."""
    return rung_index(digger.get("rung", "CLAIM")) >= 4


def board(diggers: list[dict]) -> str:
    lines = ["# Digger feed — proof ladder (advances on evidence only)"]
    for d in sorted(diggers, key=lambda x: -rung_index(x.get("rung", "CLAIM"))):
        flag = "  <-- SUBSTITUTION-READY" if substitution_ready(d) else ""
        lines.append(f"## {d.get('name')} [{d.get('rung')}]{flag}")
        lines.append(f"   kind: {d.get('kind')} | targets: {d.get('targets_edge', '-')}")
        lines.append(f"   note: {d.get('note', '')}")
    return "\n".join(lines)
