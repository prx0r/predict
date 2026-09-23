"""Concept-level dependency analysis (stdlib only).

Not tickers: CONCEPTS. One thesis per concept (memory, optics, ...);
individual stocks crash harder the more reliant they are. Reliance proxy
(order): ProphetMap layerRole primary > secondary; low moatCapture =
nowhere to hide; existing threat negatives. Concept momentum = equal-weight
supplier trailing returns. Crash rank = reliance-weighted exposure.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONCEPT_GROUPS = {
    "memory": ["memory_hbm", "memory_dram", "PML_L6"],
    "optics": ["optical_io", "PML_L8_OPT", "PML_L8_NET"],
    "compute": ["accelerators", "PML_L2", "PML_L2_5"],
    "power": ["power", "PML_L8_COOL", "PML_L11", "PML_L12"],
    "packaging": ["packaging", "PML_L5", "PML_L5_5"],
    "equipment": ["PML_L4", "PML_L3_5"],
}


def concept_report(concept_id: str) -> dict:
    g = json.loads((ROOT / "data" / "bottlenecks" / "graph_v2.json").read_text())
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    # concept = node + grouped layers merged (one thesis per concept)
    ids = CONCEPT_GROUPS.get(concept_id, [concept_id])
    group = [nodes[i] for i in ids if i in nodes]
    if not group and concept_id in nodes:
        group = [nodes[concept_id]]
    sups: dict[str, dict] = {}
    for n in group:
        for s in n.get("suppliers", []):
            t = s.get("ticker")
            if not t:
                continue
            cur = sups.setdefault(t, {"ticker": t, "via": [], "role": "secondary",
                                      "moat": None, "ai": None})
            cur["via"].append(n["id"])
            if (s.get("exposure") or "") == "primary":
                cur["role"] = "primary"
            if s.get("moat_capture") is not None:
                cur["moat"] = s["moat_capture"]
            if s.get("ai_contribution") is not None:
                cur["ai"] = s["ai_contribution"]
    try:
        threats = json.load(open(ROOT / "data" / "bottlenecks" / "threats.json"))
    except OSError:
        threats = {}
    import sys
    sys.path.insert(0, str(ROOT))
    from bneck2 import prices as P
    rows = []
    for t, s in sups.items():
        try:
            cs = P.history(t, "1y").get("closes", [])
        except Exception:
            cs = []
        ret = dd = None
        if len(cs) > 100:
            px = [c["close"] for c in cs]
            ret = px[-1] / px[0] - 1
            peak, dd = px[0], 0.0
            for p in px:
                peak = max(peak, p)
                dd = min(dd, p / peak - 1 if peak else 0.0)
        neg = threats.get(t, {}).get("negatives", 0)
        # reliance: primary role 2pts + low moat 1pt + threat 1pt (heuristic, labeled)
        reliance = (2 if s["role"] == "primary" else 0) + \
                   (1 if s["moat"] is not None and s["moat"] <= 1 else 0) + \
                   (1 if neg > 0 else 0)
        rows.append({"ticker": t, "via": s["via"], "role": s["role"],
                     "moat": s["moat"], "ret_1y": round(ret, 3) if ret is not None else None,
                     "maxdd_1y": round(dd, 3) if dd is not None else None,
                     "threats": neg, "reliance": reliance})
    rows.sort(key=lambda r: -r["reliance"])
    rets = [r["ret_1y"] for r in rows if r["ret_1y"] is not None]
    return {"concept": concept_id,
            "label": nodes.get(concept_id, {}).get("label", concept_id),
            "suppliers": len(rows),
            "concept_momentum_1y": round(sum(rets) / len(rets), 3) if rets else None,
            "crash_rank": rows,
            "thesis": f"one thesis on {concept_id}; top rows crash hardest if it breaks"}


def main() -> dict:
    import sys
    out = {}
    for c in sys.argv[1:] or ["memory", "optics", "compute", "power"]:
        try:
            out[c] = concept_report(c)
        except Exception as e:
            out[c] = {"error": str(e)[:100]}
    return out
