"""bneck belief — the second graph: claims across four clocks.

Physical graph says what depends on what. Belief graph says how likely
each dependency still holds, per clock:

  hard    documents/benchmarks/code (SEC, papers, benchmarks, repos)
  expert  calibrated forecasters (weighted by Skill_i, not followers)
  pm      prediction markets (p + volume/liquidity/spread/velocity)
  equity  security-implied valuation (the economic consensus)

Lineage (msg 18): every claim carries origin_claim_id + derived_from[].
Combination rewards INDEPENDENT convergence, not repetition volume:
readings sharing a root origin collapse to one voice before pooling.

Disagreement is the alpha:
  P_hard ~= P_expert > P_PM > P_equity   -> CONSENSUS_GAP (long dissolution / short rent)
  hype high + hard low                    -> CROWDED_NARRATIVE (unwind watch)

Stdlib only. Pure functions; JSON-serializable dicts.
"""
from __future__ import annotations

CLOCKS = ("hard", "expert", "pm", "equity")


def new_claim(id: str, edge_id: str, text: str, p: float, clock: str,
              author: str = "", ts: str = "",
              origin_claim_id: str = "", derived_from: list | None = None,
              meta: dict | None = None) -> dict:
    assert clock in CLOCKS, f"clock must be one of {CLOCKS}"
    return {"id": id, "edge_id": edge_id, "text": text,
            "p": max(0.0, min(1.0, float(p))), "clock": clock,
            "author": author, "ts": ts,
            "origin_claim_id": origin_claim_id or id,
            "derived_from": list(derived_from or []),
            "meta": dict(meta or {})}


def root_of(claim: dict, by_id: dict[str, dict]) -> str:
    """Follow derivation chain to the origin claim id (cycle-safe)."""
    seen, cur = set(), claim
    while True:
        cid = cur.get("origin_claim_id") or cur["id"]
        if cid in seen or cid == cur["id"] and not cur.get("derived_from"):
            return cid
        seen.add(cur["id"])
        parents = cur.get("derived_from") or []
        if not parents or parents[0] not in by_id:
            return cid
        cur = by_id[parents[0]]


def combine(claims: list[dict]) -> dict:
    """Pool independent roots: mean within root, mean across roots.

    Six echoes of one discovery count once. Two independent lines of
    evidence count twice. Returns pooled p + audit trail.
    """
    if not claims:
        return {"p": 0.5, "n": 0, "n_independent": 0, "roots": {}}
    by_id = {c["id"]: c for c in claims}
    roots: dict[str, list[float]] = {}
    for c in claims:
        roots.setdefault(root_of(c, by_id), []).append(c["p"])
    root_means = {r: sum(v) / len(v) for r, v in roots.items()}
    pooled = sum(root_means.values()) / len(root_means)
    return {"p": round(pooled, 3), "n": len(claims),
            "n_independent": len(roots),
            "roots": {r: round(v, 3) for r, v in root_means.items()}}


def clock_split(claims: list[dict]) -> dict[str, dict]:
    """Combine per clock: {clock: combine(...)} for the disagreement board."""
    out = {}
    for clock in CLOCKS:
        sub = [c for c in claims if c["clock"] == clock]
        if sub:
            out[clock] = combine(sub)
    return out


def disagreement(split: dict[str, dict]) -> dict:
    """Gap analysis across clocks. Missing clocks are skipped, not zeroed."""
    p = {k: v["p"] for k, v in split.items()}
    flags: list[str] = []
    hard, expert, pm, equity = (p.get(k) for k in CLOCKS)
    gap_hard_equity = (hard - equity) if hard is not None and equity is not None else None
    if hard is not None and expert is not None and pm is not None and equity is not None:
        if abs(hard - expert) <= 0.1 and hard > pm > equity and (hard - equity) >= 0.2:
            flags.append("CONSENSUS_GAP — hard+expert lead markets; dissolution/rent-repricing candidate")
    hype = max([v for k, v in p.items() if k != "hard"], default=0.0) if p else 0.0
    if hard is not None and hype - hard >= 0.4:
        flags.append("CROWDED_NARRATIVE — hype far above hard evidence; unwind watch")
    if pm is not None and equity is not None and pm - equity >= 0.25:
        flags.append("PM_LEADS_EQUITY — prediction market ahead of equity consensus")
    return {"p": {k: round(v, 3) for k, v in p.items()},
            "gap_hard_equity": round(gap_hard_equity, 3) if gap_hard_equity is not None else None,
            "flags": flags}
