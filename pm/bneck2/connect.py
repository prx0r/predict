"""bneck2 connect — unexpected connections across datastreams.

Joins, per node/ticker: kill verdicts x price drift x OpenAlex attack x
HN narrative heat x HF implementation heat x whale consensus x pm spreads
x severity/conviction. Each rule is a pure function on assembled context;
scores add per leg present. Surprises (legs disagreeing) rank highest —
agreement is expected, disagreement is the finding.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> list[dict]:
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip()]
    except (OSError, ValueError):
        return []


def assemble(root: Path = ROOT) -> dict:
    """Gather local streams (no network). Live top-ups happen in run()."""
    b = root / "data" / "beliefs"
    return {
        "verdicts": _load_jsonl(b / "kill_observations.jsonl"),
        "signals": _load_jsonl(b / "signals.jsonl"),
        "severity_hist": _load_jsonl(root / "data" / "bottlenecks" / "severity_history.jsonl"),
    }


def latest_verdicts(verdicts: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    for r in verdicts:
        by.setdefault(r.get("node_id", "?"), []).append(r)
    return {k: v[-3:] for k, v in by.items()}


def rule_burst_drift(node_id: str, tickers: list[str],
                     verdicts: list[dict], fwd: dict[str, float | None]) -> dict | None:
    trig = [r for r in verdicts if r.get("verdict") == "TRIGGERED"
            and "sec-burst" in r.get("signal", "")]
    if not trig:
        return None
    rets = {t: fwd[t] for t in tickers if fwd.get(t) is not None}
    if not rets:
        return None
    return {"rule": "burst_drift", "node": node_id,
            "burst": trig[0]["measured"][:80],
            "forwards": rets,
            "legs": 2,
            "note": f"burst + {len(rets)} forward returns on record"}


def rule_attack_narrative(node_id: str, attack_tier: str,
                          heat: dict) -> dict | None:
    if attack_tier != "HIGH" or heat.get("heat") != "HIGH":
        return None
    return {"rule": "attack_narrative", "node": node_id, "legs": 2,
            "note": f"research attack + HN heat HIGH ({heat['points']}pts): "
                    f"saturation — WATCH not buy"}


def rule_whale_node(node_id: str, signals: list[dict]) -> dict | None:
    hits = [s for s in signals if s.get("type") == "WHALE_CONSENSUS"
            and str(s.get("ticker", "")).lower() == node_id]
    if not hits:
        return None
    s = hits[-1]
    return {"rule": "whale_node", "node": node_id, "legs": 2,
            "note": f"whale consensus str={s.get('strength')} "
                    f"conf={s.get('confidence')}: {str(s.get('source', ''))[:100]}"}


def rule_pm_spread(topic: str, readings: list[dict]) -> dict | None:
    """Max-min p across venues on one topic >= 0.25 => triangulation gap."""
    ps = [r["p"] for r in readings if isinstance(r.get("p"), (int, float))]
    if len(ps) < 2:
        return None
    gap = max(ps) - min(ps)
    if gap < 0.25:
        return None
    return {"rule": "pm_spread", "node": topic, "legs": len(ps),
            "note": f"venue disagreement {gap:.2f}: " +
                    ", ".join(f"{r.get('venue','?')}={r['p']}" for r in readings[:4])}


def rule_severity_price(node_id: str, b: float, dbdt: float,
                        momentum: float | None) -> dict | None:
    if momentum is None:
        return None
    divergent = (dbdt > 0.05 and momentum < -0.03) or (b > 0.3 and momentum < -0.05)
    if not divergent:
        return None
    return {"rule": "severity_price", "node": node_id, "legs": 2,
            "note": f"B={b:.2f} dB/dt={dbdt:+.3f} but 5d momentum {momentum:+.1%}: "
                    f"price disagrees with scarcity — dig here"}


def rank(rows: list[dict | None]) -> list[dict]:
    out = [r for r in rows if r]
    out.sort(key=lambda r: (-r.get("legs", 1), r.get("rule", "")))
    return out


def render(rows: list[dict]) -> str:
    lines = ["# Unexpected connections — cross-stream joins"]
    if not rows:
        lines.append("no multi-leg connections this pass.")
        return "\n".join(lines)
    for r in rows:
        lines.append(f"  [{r['rule']}] {r.get('node', '?')} ({r.get('legs', 1)} legs): {r['note'][:220]}")
    return "\n".join(lines)


def rule_insider_cluster(node: str, rows: list[dict],
                         min_usd: float = 500000.0) -> dict | None:
    """Multi-insider buying one name (cluster page = pre-joined).
    Caller pre-filters rows to the node; min_usd per row."""
    hits = [r for r in rows if r.get("value_usd", 0) >= min_usd]
    if not hits:
        return None
    tot = sum(h["value_usd"] for h in hits)
    return {"rule": "insider_cluster", "node": node, "legs": 2,
            "note": f"{len(hits)} cluster rows ${tot:,.0f}: " +
                    ", ".join(h.get("insider", "")[:20] for h in hits[:3])}


def rule_short_crowded(ticker: str, short_ratio: float | None,
                       crowdedness: float) -> dict | None:
    """High short interest on a crowded long = squeeze-or-funeral watch."""
    if short_ratio is None or short_ratio < 0.4 or crowdedness < 0.6:
        return None
    return {"rule": "short_crowded", "node": ticker, "legs": 2,
            "note": f"short ratio {short_ratio:.0%} + crowdedness "
                    f"{crowdedness:.2f}: positioned both ways, watch"}
