"""bneck jevons — the single biggest trap: expansion vs substitution.

Every KILL hypothesis needs two numbers:
  efficiency_gain   fraction of X removed per unit (0.8 = 80% less HBM/token)
  demand_elasticity demand multiplier from cheaper output (20x tokens)

  residual = (1 - gain) * elasticity
  residual < 1  -> SUBSTITUTION: demand for X falls (short thesis valid)
  residual >= 1 -> EXPANSION: Jevons trap — X gets MORE constrained

Example: 80% less HBM/token but 20x tokens -> 0.2*20 = 4.0 -> EXPANSION.
The digger makes us use MORE picks. Shorting into that is suicide.

Stdlib only. Pure functions.
"""
from __future__ import annotations


def classify(efficiency_gain: float, demand_elasticity: float) -> dict:
    residual = (1.0 - float(efficiency_gain)) * float(demand_elasticity)
    verdict = "SUBSTITUTION" if residual < 1.0 else "EXPANSION"
    return {"verdict": verdict, "residual_demand": round(residual, 3),
            "efficiency_gain": efficiency_gain, "demand_elasticity": demand_elasticity,
            "note": ("demand for X falls — short thesis valid"
                     if verdict == "SUBSTITUTION"
                     else "Jevons trap — X tightens; do NOT short on efficiency alone")}


def check_kill(node: dict, efficiency_gain: float, demand_elasticity: float) -> dict:
    """Attach the Jevons verdict to a node's kill hypothesis."""
    out = classify(efficiency_gain, demand_elasticity)
    out["node"] = node.get("id")
    out["allowed"] = out["verdict"] == "SUBSTITUTION"
    return out
