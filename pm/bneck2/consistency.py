"""bneck2 consistency — World-State Consistency Arbitrage (thesis §§36-37).

Don't predict 2030. Infer the world each price requires, then test the
conjunction: find (incumbent, world) pairs where the market jointly prices
HIGH survival for the incumbent AND HIGH probability for a world that
impairs it. Those two prices cannot both be right.

Needs only worlds.json (survives maps + p_market + market_survival_p).
Cross-incumbent exclusivity clusters are queued until worlds carry
mutually-exclusive tags (documented, not faked).
"""
from __future__ import annotations


def find_inconsistencies(doc: dict, min_gap: float = 0.25) -> list[dict]:
    """Ranked [{incumbent, world, market_survival, p_market_world,
    survives_in_world, score}]. score = gap x p_market(w)."""
    out = []
    for inc in doc.get("incumbents", []):
        surv = inc.get("survives", {})
        mkt_surv = float(inc.get("market_survival_p", 1.0))
        for w in doc.get("worlds", []):
            s = float(surv.get(w["id"], 1.0))
            if s >= 0.5:
                continue
            gap = mkt_surv - s
            if gap < min_gap:
                continue
            pm = float(w.get("p_market", 0.0))
            out.append({"incumbent": inc.get("id"), "world": w["id"],
                        "market_survival": mkt_surv,
                        "p_market_world": pm, "survives_in_world": s,
                        "score": round(gap * pm, 4)})
    out.sort(key=lambda r: -r["score"])
    return out


def render(rows: list[dict], top: int = 10) -> str:
    lines = ["# World-State Consistency Arbitrage — market prices requiring "
             "contradictory worlds"]
    if not rows:
        lines.append("no inconsistencies at current thresholds.")
        return "\n".join(lines)
    for r in rows[:top]:
        lines.append(f"  {r['score']:.3f} {r['incumbent']} survives@{r['market_survival']:.2f} "
                     f"but '{r['world']}' (p_mkt={r['p_market_world']:.2f}) impairs it "
                     f"(surv={r['survives_in_world']:.2f})")
    return "\n".join(lines)
