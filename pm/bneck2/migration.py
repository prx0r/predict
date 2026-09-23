"""bneck2 migration — scarcity-migration engine (thesis §40 + §§1-14).

Implements what the scarcity-migration thesis makes newly modelable, stdlib:

  B_i (severity) = induced x indispensability x replacement x permission
                   / (substitutes + eps)            [endogenous severity]
  dB_i/dt        = severity velocity across passes  [acceleration, not level]
  X_i (cross-world exposure) = SUM_s P_you(s) x need_i(s)
  release P      = supply-response Laplace rate from verdict history
  catalytic edge = A raises the *hazard rate* of B's breakthrough (dynamic)
  derivative     = what binds next if this node is relieved (CASCADE +
                   dependents)
  alpha_v2       = gap x dCF x X x B x R - C   [master equation, §40]

Honesty rules: every factor has a documented neutral default; node fields
not yet measured (permission_friction, replacement_years, irreducibility)
fall back to priors in PERMISSION_PRIORS / code defaults, flagged via
`estimated: True` in outputs. No fabrication: missing readings -> neutral,
never bullish.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "data" / "bottlenecks" / "severity_history.jsonl"

EPS = 1e-6

# Evidence-backed permission priors (thesis §§5-6, 13). Everything else 0.5.
# power: IEA 2500GW queues, 5-15y grid vs 1-3y DC build, FERC readiness push.
# export_controls: licenses are the constraint by definition.
# experimentation: FDA/clinical validation gates (thesis §6, §13 bio I/O).
PERMISSION_PRIORS = {
    "power": 0.85,
    "export_controls": 0.9,
    "experimentation": 0.7,
    "quantum_ip": 0.6,
}

# Economic Transfer Score tiers (thesis §22): evidence rank by proximity to
# verified cash-flow impact. Benchmarks deliberately low (mineability).
TRANSFER_SCORE = {
    "benchmark": 0.30,
    "model_eval": 0.40,
    "third_party_repro": 0.55,
    "real_workflow": 0.65,
    "novel_task": 0.70,
    "autonomous_operation": 0.78,
    "physical_experiment": 0.85,
    "willingness_to_pay": 0.90,
    "production_deployment": 0.95,
    "verified_cashflow": 1.00,
}

CATALYTIC = "CATALYZES"


def transfer_weight(kind: str) -> float:
    return TRANSFER_SCORE.get((kind or "").lower(), 0.5)


def permission_friction(node: dict) -> tuple[float, bool]:
    if "permission_friction" in node:
        return float(node["permission_friction"]), False
    return PERMISSION_PRIORS.get(node.get("id", ""), 0.5), True


def severity(node: dict, reading: dict | None = None) -> dict:
    """Endogenous bottleneck severity B_i (thesis §40)."""
    reading = reading or {}
    induced = float(reading.get("demand_growth") if reading.get("demand_growth") is not None else 1.0)
    indispensability = float(node.get("revenue_purity") if node.get("revenue_purity") is not None else 0.5)
    repl_years = float(node.get("replacement_years") if node.get("replacement_years") is not None else (node.get("td_years") if node.get("td_years") is not None else 3.0))
    replacement = min(max(repl_years / 10.0, 0.0), 1.0)
    perm, perm_est = permission_friction(node)
    permission = 0.5 + 0.5 * perm
    substitutes = float(node.get("substitutability") if node.get("substitutability") is not None else 0.5)
    b = induced * indispensability * replacement * permission / (substitutes + EPS)
    return {"B": round(b, 4), "induced": induced,
            "indispensability": indispensability,
            "replacement_norm": round(replacement, 3),
            "permission": perm, "permission_estimated": perm_est,
            "substitutes": substitutes}


def record_severity(node_id: str, b: float, ts: str,
                    path: Path = HISTORY_PATH) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": ts, "node_id": node_id, "B": b}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load_history(path: Path = HISTORY_PATH) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []


def velocity(node_id: str, history: list[dict] | None = None) -> dict:
    """dB/dt per year + acceleration from successive severity snapshots."""
    rows = [r for r in (history if history is not None else load_history())
            if r.get("node_id") == node_id]
    if len(rows) < 2:
        return {"dB_dt": 0.0, "accel": 0.0, "n": len(rows)}
    bs = [float(r["B"]) for r in rows[-3:]]
    # Timestamps ISO; fall back to even spacing when unparseable.
    def yr(ts: str) -> float:
        try:
            return int(str(ts)[:4]) + int(str(ts)[5:7]) / 12.0
        except (ValueError, IndexError):
            return 0.0
    ts = [yr(r.get("ts", "")) for r in rows[-3:]]
    if ts[-1] <= ts[0]:
        ts = list(range(len(bs)))
        span = 1.0
    else:
        span = ts[-1] - ts[0]
    d1 = (bs[-1] - bs[0]) / span if span > 0 else 0.0
    accel = 0.0
    if len(bs) == 3:
        span2 = (ts[2] - ts[1]) or span / 2.0 or 1.0
        span1 = (ts[1] - ts[0]) or span / 2.0 or 1.0
        accel = (bs[2] - bs[1]) / span2 - (bs[1] - bs[0]) / span1
    return {"dB_dt": round(d1, 4), "accel": round(accel, 4), "n": len(rows)}


def cross_world_exposure(incumbent: dict, worlds: list[dict]) -> dict:
    """X_i = SUM_s P_you(s) x need_i(s); need = 1 - survival in s."""
    surv = incumbent.get("survives", {})
    terms, x = [], 0.0
    for w in worlds:
        need = 1.0 - float(surv.get(w["id"], 1.0))
        contrib = float(w.get("p_you") if w.get("p_you") is not None else 0.0) * need
        x += contrib
        terms.append({"world": w["id"], "p_you": w.get("p_you"),
                      "need": round(need, 3), "x": round(contrib, 4)})
    return {"incumbent": incumbent.get("id"), "X": round(x, 4), "terms": terms}


def release_probability(node_id: str, observations: list[dict]) -> dict:
    """Bottleneck-release P from supply-response verdicts (Laplace-smoothed).

    Supply keywords separate self-dug release (capacity, inventory, orders,
    lead-time) from architectural kills — thesis §8: don't mix them.
    """
    supply_words = ("capacity", "inventory", "order", "lead-time", "lead time",
                    "oversupply", "cancellation", "spot price")
    rows = [r for r in observations if r.get("node_id") == node_id]
    sup = [r for r in rows if any(w in (r.get("signal", "") + r.get("measured", "")).lower()
                                  for w in supply_words)]
    trig = sum(1 for r in sup if r.get("verdict") == "TRIGGERED")
    return {"node_id": node_id, "n_supply": len(sup), "n_triggered": trig,
            "P_release": round((trig + 1) / (len(sup) + 2), 4)}


def catalytic_edges(graph: dict) -> list[dict]:
    """CATALYZES edges: A raises B's breakthrough hazard (thesis §1)."""
    return [e for e in graph.get("edges", []) if e.get("relation") == CATALYTIC]


def hazard_update(prior_hazard: float, catalysts: list[dict]) -> float:
    """h_B' = h_B x (1 + SUM strength x automation_event). Pure."""
    mult = 1.0
    for c in catalysts:
        mult += float(c.get("strength") if c.get("strength") is not None else 0.0) * float(c.get("event") if c.get("event") is not None else 0.0)
    return round(float(prior_hazard) * mult, 6)


def bottleneck_derivative(node_id: str, graph: dict) -> list[dict]:
    """What binds next if node_id is relieved: CASCADE targets (demand
    unlocks downstream) + DEPENDS_ON sources (dependents surge)."""
    out = []
    for e in graph.get("edges", []):
        # DEPENDS_ON points dependent -> prerequisite: relief of the
        # prerequisite lets dependents surge.
        if e.get("target") == node_id and e.get("relation") == "DEPENDS_ON":
            out.append({"node": e["source"], "via": "dependent-surge"})
    for e in graph.get("edges", []):
        if e.get("source") == node_id and e.get("relation") == "CASCADE":
            out.append({"node": e["target"], "via": "cascade-unlock"})
    seen, dedup = set(), []
    for r in out:
        if r["node"] not in seen:
            seen.add(r["node"])
            dedup.append(r)
    return dedup


def alpha_v2(belief_gap: float, dcf: float, x: float, b: float, r: float,
             crowdedness: float) -> float:
    """Master equation §40: gap x dCF x X x B x R - C."""
    return round(belief_gap * dcf * x * b * r - crowdedness, 4)


def deliverable_mw(announced_mw: float, probs: dict[str, float]) -> dict:
    """Deliverable MW = announced x P(site) x P(interconnect) x P(xfmr) x
    P(generation) x P(permit) (goated §5). Missing factors -> neutral is
    WRONG here (overstates); missing -> 0.5 flagged estimated."""
    legs = ("site", "interconnect", "transformer", "generation", "permit")
    est = [k for k in legs if k not in probs]
    p = 1.0
    for k in legs:
        p *= float(probs.get(k, 0.5))
    return {"deliverable_mw": round(float(announced_mw) * p, 1),
            "derate": round(p, 4), "estimated_legs": est}


def surprise_update(prior: float, llr: float, credibility: float) -> dict:
    """ΔP(W) ∝ Surprise x Credibility (goated §21). Caller supplies the
    log-likelihood ratio of the *residual* (pure news); credibility tempers.
    Logit-domain update, same family as updater.fuse."""
    p = min(max(float(prior), 1e-9), 1 - 1e-9)
    c = min(max(float(credibility), 0.0), 1.0)
    l = math.log(p / (1 - p)) + c * float(llr)
    post = 1 / (1 + math.exp(-l))
    return {"prior": prior, "posterior": round(post, 4),
            "delta": round(post - prior, 4)}


# Economic threshold cliffs (goated §28): cost at which demand goes
# discontinuous. proximity = current/threshold; <=1 crossed.
CLIFFS = {
    "robot_hour_usd": 4.0,
    "inference_task_usd": 0.03,
    "assay_sample_usd": 1.0,
    "transmission_mw_cost": 1.0,  # placeholder unit; needs calibration
}


def cliff_proximity(cliff_id: str, current_cost: float) -> dict:
    t = CLIFFS.get(cliff_id)
    if t is None or current_cost is None:
        return {"cliff": cliff_id, "proximity": None, "crossed": None}
    return {"cliff": cliff_id, "threshold": t,
            "proximity": round(float(current_cost) / t, 3),
            "crossed": float(current_cost) <= t}


def tech_half_life(tk_years: float | None) -> float | None:
    """H_tech proxy from time-to-kill: faster kill -> shorter half-life.
    Explicit proxy, not a measurement (goated §§25-26)."""
    if tk_years is None:
        return None
    return round(float(tk_years) / 2.0, 2)


def duration_mismatch(h_valuation: float | None,
                      h_tech: float | None) -> dict:
    """DurationMismatch = H_valuation - H_tech. Positive = short candidate.
    Either leg missing -> INSUFFICIENT, never zero (zero would read safe)."""
    if h_valuation is None or h_tech is None:
        return {"mismatch": None, "verdict": "INSUFFICIENT"}
    m = round(float(h_valuation) - float(h_tech), 2)
    return {"mismatch": m,
            "verdict": "SHORT_CANDIDATE" if m >= 2.0 else "OK"}
