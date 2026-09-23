"""bneck ceo — executive-capital OSINT with honesty boundaries.

Form 4 / 13D/G / 13F / Form D / proxies / disclosed funds give EXCELLENT
data for public-company insiders. There is NO complete public database of
a private-company executive's personal portfolio (e.g. Sam Altman) — so
this module keeps two ledgers and never mixes them:

  known:   verified transactions with sources
  unknown: explicitly flagged gaps (person, domain, why-unknown)

Hallucinating holdings is a correctness violation, not a data gap.
Stdlib only. Store: data/labs/ceo.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CEO_PATH = ROOT / "data" / "labs" / "ceo.json"


def load_ledger(path: Path = CEO_PATH) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        d.setdefault("known", [])
        d.setdefault("unknown", [])
        return d
    except (OSError, ValueError):
        return {"known": [], "unknown": []}


def save_ledger(d: dict, path: Path = CEO_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=1), encoding="utf-8")


def add_known(d: dict, person: str, date: str, vehicle: str, detail: str,
              source: str) -> dict:
    d["known"].append({"person": person, "date": date, "vehicle": vehicle,
                       "detail": detail, "source": source})
    return d


def flag_unknown(d: dict, person: str, domain: str, why: str) -> dict:
    if not any(u["person"] == person and u["domain"] == domain for u in d["unknown"]):
        d["unknown"].append({"person": person, "domain": domain,
                             "why_unknown": why, "status": "gap"})
    return d


def report(d: dict) -> str:
    lines = ["# Executive capital — known vs unknown",
             f"Known transactions: {len(d['known'])} | flagged gaps: {len(d['unknown'])}"]
    for k in d["known"][-10:]:
        lines.append(f"  KNOWN {k['date']} {k['person']} via {k['vehicle']}: {k['detail']} [{k['source']}]")
    for u in d["unknown"]:
        lines.append(f"  UNKNOWN {u['person']} / {u['domain']}: {u['why_unknown']}")
    return "\n".join(lines)
