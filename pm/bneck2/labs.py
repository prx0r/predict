"""bneck labs — frontier-lab moat tracker: what the labs buy.

Labs training frontier models see bottlenecks first (their walls are the
world's early warning). Their acquisitions/investments/JVs reveal which
constraints they believe are binding — and the ABSENCE of buying in a layer
(compute substrates) is itself a signal: they don't yet believe, or they
plan to build.

Tags: deployment-labor | agent-infra | devices | distribution-media |
models-talent | compute-substrate | data-energy | services.

substrate_gap(): share of compute-substrate deals. ~0 means no lab has
moved on novel compute — the Nvidia-coverage event (a lab buying into
thermodynamic/probabilistic/neuromorphic) would be a regime signal.

Seed: data/labs/deals.json (verified 2025-2026 items only). Stdlib only.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEALS_PATH = ROOT / "data" / "labs" / "deals.json"

SUBSTRATE_TAGS = {"compute-substrate"}


def load_deals(path: Path = DEALS_PATH) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("deals", [])
    except (OSError, ValueError):
        return []


def attention_by_tag(deals: list[dict]) -> dict:
    n = Counter()
    amt: dict[str, float] = Counter()
    for d in deals:
        tag = d.get("tag", "unknown")
        n[tag] += 1
        if d.get("amount_usd"):
            amt[tag] += d["amount_usd"]
    return {"by_count": dict(n.most_common()),
            "by_amount_usd": {k: v for k, v in amt.most_common()}}


def substrate_share(deals: list[dict]) -> dict:
    sub = [d for d in deals if d.get("tag") in SUBSTRATE_TAGS]
    return {"substrate_deals": len(sub), "total_deals": len(deals),
            "share": round(len(sub) / len(deals), 3) if deals else 0.0,
            "items": [(d.get("lab"), d.get("target")) for d in sub]}


def gap_report(deals: list[dict]) -> str:
    att = attention_by_tag(deals)
    sub = substrate_share(deals)
    lines = ["# Frontier-lab moat — where the labs put money",
             f"Tracked deals: {sub['total_deals']} | compute-substrate share: {sub['share']:.1%}",
             "\nAttention by count:"]
    for tag, c in att["by_count"].items():
        lines.append(f"  {tag:20} {c}")
    if att["by_amount_usd"]:
        lines.append("Attention by disclosed $:")
        for tag, a in att["by_amount_usd"].items():
            lines.append(f"  {tag:20} ${a:,.0f}")
    lines.append("\nSubstrate gap: " + (
        "NO lab has bought into novel compute substrates — "
        "watch for the first thermodynamic/probabilistic/neuromorphic "
        "acquisition or strategic investment as an Nvidia-coverage signal."
        if sub["substrate_deals"] == 0 else
        f"{sub['substrate_deals']} substrate deal(s): {sub['items']}"))
    return "\n".join(lines)


# --- Revealed preference (msg 20): FRONTIER_LAB_CAPITAL_COMMITMENT ---
# LabSignal = log(1+$) * Irreversibility * Specificity * Relevance * Duration
# A tweet scores ~nothing; a 22-year nuclear contract scores enormously.
# Commitments (infra, silicon roadmaps, capacity) live in
# data/labs/commitments.json — separate from acquisitions (deals.json).

import math

COMMITMENTS_PATH = ROOT / "data" / "labs" / "commitments.json"

# Irreversibility guide by commitment kind (analyst-set, documented).
IRREVERSIBILITY = {
    "tweet": 0.05,
    "acquisition": 0.5,
    "investment": 0.4,
    "silicon-roadmap": 0.7,
    "deployment": 0.85,
    "capacity-contract": 0.9,
    "multidecade-contract": 1.0,
}


def load_commitments(path: Path = COMMITMENTS_PATH) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("commitments", [])
    except (OSError, ValueError):
        return []


def lab_signal(entry: dict) -> dict:
    """Score one capital commitment. Undisclosed $ falls back to size_proxy_usd
    (flagged estimated) so strategic-but-unpriced moves still rank."""
    amount = entry.get("amount_usd")
    estimated = False
    if amount is None:
        amount = entry.get("size_proxy_usd", 0)
        estimated = True
    irrev = float(entry.get("irreversibility",
                            IRREVERSIBILITY.get(entry.get("kind", ""), 0.3)))
    spec = float(entry.get("specificity", 0.5))
    rel = float(entry.get("relevance", 0.5))
    duration = min(float(entry.get("duration_years", 1.0)), 25.0) / 25.0
    score = math.log1p(max(0.0, float(amount))) * irrev * spec * rel * duration
    return {"score": round(score, 3), "amount_usd": amount or 0,
            "estimated_amount": estimated, "irreversibility": irrev,
            "duration_norm": round(duration, 3),
            # Tie-break when $ is unknown (no fabrication): strategic weight
            # so unpriced moves order by conviction, never input order.
            "tiebreak": round(irrev * spec * rel * duration, 4)}


def rank_commitments(entries: list[dict]) -> list[dict]:
    out = [{**e, **lab_signal(e)} for e in entries]
    out.sort(key=lambda x: (-x["score"], -x["tiebreak"]))
    return out


def diversification_reading(entries: list[dict], lab: str = "OpenAI") -> str:
    """N accelerator architectures committed = no-single-architecture thesis."""
    kinds = {e.get("target", "") for e in entries if e.get("lab") == lab}
    arch = {k for k in kinds if any(s in k.lower() for s in
            ("cerebras", "trainium", "amd", "broadcom", "nvidia", "jalapeno"))}
    if len(arch) >= 4:
        return (f"{lab} committed across {len(arch)} accelerator architectures "
                f"({', '.join(sorted(arch))}): revealed belief = no single "
                "architecture is safe to treat as permanent. NVIDIA persistence "
                "must be scored down, not assumed.")
    return f"{lab}: {len(arch)} architectures tracked — below diversification threshold."
