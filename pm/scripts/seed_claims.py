#!/usr/bin/env python3
"""Seed data/beliefs/claims.json from worlds.json (provenance-tagged).

Un-stubs the `status.py --belief` board: each world becomes an expert claim
(p_you) + a pm claim (p_market); each incumbent becomes an equity claim
(market-priced survival). Seeds carry origin=seed:worlds.json and are the
ONLY rows this script touches on re-run — hand-added claims are preserved.

Usage: /usr/bin/python3 scripts/seed_claims.py [--force]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import worlds as W  # noqa: E402

CLAIMS_PATH = ROOT / "data" / "beliefs" / "claims.json"
SEED = "seed:worlds.json"


def clock_meta() -> dict:
    """Three clocks (thesis §17): capability / deployment / cash-flow time.
    Null until measured — markets collapse them into one date; we don't."""
    return {"t_capability": None, "t_deployment": None, "t_cashflow": None}


def build_claims(doc: dict) -> list[dict]:
    out: list[dict] = []
    for w in doc.get("worlds", []):
        out.append({"id": f"seed-{w['id']}-expert", "edge_id": w["id"],
                    "text": f"seed expert: {w.get('label', w['id'])}",
                    "p": w["p_you"], "clock": "expert", "author": SEED,
                    "origin_claim_id": "", "derived_from": [],
                    "meta": clock_meta()})
        out.append({"id": f"seed-{w['id']}-pm", "edge_id": w["id"],
                    "text": f"seed market-implied: {w.get('label', w['id'])}",
                    "p": w["p_market"], "clock": "pm", "author": SEED,
                    "origin_claim_id": "", "derived_from": [],
                    "meta": clock_meta()})
    for inc in doc.get("incumbents", []):
        out.append({"id": f"seed-{inc['id']}-equity", "edge_id": inc["id"],
                    "text": f"seed equity-priced survival: "
                    f"{inc.get('label', inc['id'])}",
                    "p": inc.get("market_survival_p", 1.0), "clock": "equity",
                    "author": SEED, "origin_claim_id": "", "derived_from": [],
                    "meta": clock_meta()})
    return out


def main() -> int:
    force = "--force" in sys.argv[1:]
    try:
        cur = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = []
    hand = [c for c in cur if c.get("author") != SEED]
    if hand and not force and cur:
        print(f"claims.json has {len(hand)} hand-added claims; "
              f"refusing to touch without --force ({len(cur)} rows kept).")
        return 0
    doc = W.load_worlds()
    seeded = build_claims(doc)
    CLAIMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAIMS_PATH.write_text(json.dumps(hand + seeded, indent=1),
                           encoding="utf-8")
    print(f"claims.json: {len(hand)} hand-kept + {len(seeded)} seeded "
          f"({len(doc.get('worlds', []))} worlds).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
