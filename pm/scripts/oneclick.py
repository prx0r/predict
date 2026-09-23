#!/usr/bin/env python3
"""One-click experimentation loop — all datastreams, one report.

Runs: Yahoo poll -> killfeed live -> migration board -> experiments all ->
cross-stream connections -> backtest panel append/fill/run -> markdown
report (docs/ONECLICK-<ts>.md) + stdout summary.

Every step degrades gracefully (a dead venue never kills the loop).
Backtest reports INSUFFICIENT until >=2 complete forward dates exist.
"""
from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STEPS: list[str] = []


def step(name: str, fn):
    t0 = time.time()
    try:
        out = fn()
        STEPS.append(f"OK   {name} ({time.time()-t0:.0f}s) {out or ''}")
    except Exception as exc:
        STEPS.append(f"FAIL {name}: {str(exc)[:140]}")
        traceback.print_exc(limit=2)


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"# oneclick {ts}")

    hb = ROOT / "data" / "heartbeat.json"
    try:
        import json as _j
        last = _j.loads(hb.read_text(encoding="utf-8")).get("ts", "")
        from datetime import datetime as _dt
        gap = (datetime.now(timezone.utc) - _dt.fromisoformat(last)).total_seconds() / 3600
        if gap > 30:
            print(f"!! HEARTBEAT GAP {gap:.0f}h (>30h) — clock stopped, this pass is the recovery")
    except Exception:
        print("!! no heartbeat on record — first tracked pass")

    def do_poll():
        from bneck2 import prices as P
        moves = P.get_moves(sorted(P.YAHOO_MAP))
        ok = sum(1 for v in moves.values() if "price" in v)
        return f"{ok}/{len(moves)} priced"

    def do_killfeed():
        from bneck2 import killfeed as K
        s = K.run(live=True, write=True)
        return f"{s['verdicts']} verdicts, {len(s['triggered'])} triggered"

    def do_migration():
        from bneck2 import graph as G
        from bneck2 import migration as M
        from bneck2 import quant as Q
        g = G.load_graph()
        readings = Q.load_readings()
        rows = Q.score_all(g, readings)
        sev = {r["id"]: M.severity(
            next(n for n in g["nodes"] if n["id"] == r["id"]),
            readings.get(r["id"]))["B"] for r in rows}
        top = sorted(sev.items(), key=lambda kv: -kv[1])[:3]
        return "top-B: " + ", ".join(f"{k}={v:.2f}" for k, v in top)

    def do_experiments():
        from bneck2 import experiments as X
        from bneck2 import lab as LAB
        got = []
        for hid, fn in sorted(X.REGISTRY.items()):
            try:
                result, verdict, n = fn()
            except Exception as exc:
                result, verdict, n = {"error": str(exc)[:150]}, "INCONCLUSIVE", 0
            LAB.receipt(hid, result, verdict, n,
                          comparisons=int(result.get("comparisons", 1)))
            got.append(f"{hid}:{verdict[0]}")
        return " ".join(got)

    def do_connect():
        return connect_pass()

    def do_resolve():
        from bneck2 import lab as LAB
        from bneck2 import resolve as R
        done = LAB.resolve_due(R.resolve)
        hits = sum(1 for r in done if r.get("hit"))
        return f"{hits}/{len(done)} hits"

    def do_backtest():
        from bneck2 import backtest as BT
        from bneck2 import graph as G
        from bneck2 import quant as Q
        g = G.load_graph()
        rows = Q.score_all(g, Q.load_readings())
        scores: dict[str, float] = {}
        for r in rows:
            node = next(n for n in g["nodes"] if n["id"] == r["id"])
            for t in node.get("tickers", []):
                scores[t] = round(r["binding"] - r["dissolution"], 3)
        date = ts[:10]
        n_new = BT.append_snapshot(date, scores)
        n_fill = BT.fill_forwards()
        res = BT.live_result()
        return f"+{n_new} scores, +{n_fill} forwards, {res.get('status')}: " \
               f"{res.get('sharpe', res.get('need', ''))}"

    step("poll", do_poll)
    step("killfeed-live", do_killfeed)
    step("migration", do_migration)
    step("experiments", do_experiments)
    step("connect", do_connect)
    step("resolve", do_resolve)
    step("backtest", do_backtest)

    body = f"# One-click loop — {ts}\n\n" + "\n".join(f"- {s}" for s in STEPS)
    body += "\n\n" + connect_render()
    out = ROOT / "docs" / f"ONECLICK-{ts.replace(':', '')}.md"
    out.write_text(body + "\n", encoding="utf-8")
    print("\n".join(STEPS))
    import json as _j2
    hb.write_text(_j2.dumps({"ts": ts, "steps": STEPS}), encoding="utf-8")
    print(f"report: {out}")
    return 0


_CONNECT_RENDER = ""


def connect_render() -> str:
    return _CONNECT_RENDER


def connect_pass() -> str:
    """Bounded live top-ups + rule joins across streams."""
    global _CONNECT_RENDER
    from collectors import hf as HF
    from collectors import hn as HN
    from collectors import manifold as MF
    from bneck2 import connect as C
    from bneck2 import graph as G
    from bneck2 import migration as M
    from bneck2 import prices as P
    from bneck2 import quant as Q
    from bneck2 import worlds as W

    g = G.load_graph()
    readings = Q.load_readings()
    ctx = C.assemble()
    latest = C.latest_verdicts(ctx["verdicts"])
    sev = {n["id"]: M.severity(n, readings.get(n["id"]))["B"] for n in g["nodes"]}
    top_nodes = sorted(sev, key=lambda k: -sev[k])[:5]

    # Bounded live top-ups (5 HN + 5 HF + 3 Manifold topics + lab feeds).
    heats, impls = {}, {}
    for nid in top_nodes:
        node = next(n for n in g["nodes"] if n["id"] == nid)
        q = node.get("label", nid)
        hits = HN.fetch_stories(q, 10)
        heats[nid] = HN.narrative_heat(hits)
        impls[nid] = HF.implementation_heat(HF.fetch_models(q.split("/")[0].strip(), 10))
        time.sleep(0.5)
    mani = []
    for topic in ("artificial intelligence", "nuclear power", "quantum computer"):
        mani += [{"topic": topic, **r} for r in MF.fetch_markets(topic, 5)]
        time.sleep(0.5)

    # Lab announcements x bottleneck nodes (capability posts imply demand).
    from collectors import labs_rss as LR
    from bneck2 import scarcity as SC

    # Price momentum for burst tickers + top nodes.
    tickers = sorted({t for n in g["nodes"] for t in n.get("tickers", []) if t.isupper()})
    fwd, mom = {}, {}
    for t in tickers[:14]:
        fr = P.forward_return(t, "2026-09-03", 4)
        if fr.get("return") is not None:
            fwd[t] = fr["return"]
        h = P.history(t).get("closes", [])[-6:]
        if len(h) == 6 and h[0]["close"]:
            mom[t] = round((h[-1]["close"] - h[0]["close"]) / h[0]["close"], 4)
        time.sleep(0.3)

    lab_rows = []
    for lab in ("openai", "deepmind"):
        for p in LR.capability_hits(LR.lab_posts(lab, 20)):
            hits = SC.scan_text(p["title"])
            for h in hits[:2]:
                if h["node_id"]:
                    lab_rows.append({"rule": "lab_node", "node": h["node_id"],
                                     "legs": 2,
                                     "note": f"{lab}: {p['title'][:100]}"})
        time.sleep(0.5)
    rows = []
    for n in g["nodes"]:
        nid = n["id"]
        v = latest.get(nid, [])
        atk_rows = [r for r in v if r.get("source") == "openalex"]
        tier = ("HIGH" if any(r.get("verdict") == "TRIGGERED"
                              for r in atk_rows) else "normal")
        rows.append(C.rule_attack_narrative(nid, tier, heats.get(nid, {})))
        rows.append(C.rule_whale_node(nid, ctx["signals"]))
        b = sev.get(nid, 0.0)
        for t in n.get("tickers", []):
            rows.append(C.rule_severity_price(nid, b, 0.0, mom.get(t)))
    # Venue triangulation per topic.
    by_topic: dict[str, list[dict]] = {}
    for r in mani:
        by_topic.setdefault(r["topic"], []).append(r)
    for topic, rs in by_topic.items():
        rows.append(C.rule_pm_spread(topic, rs))

    # Insider clusters + short flow (bounded: 3 calls, mapped to nodes).
    from collectors import finra as FIN
    from collectors import openinsider as OI
    tick_to_node: dict[str, str] = {}
    for n in g["nodes"]:
        for t in n.get("tickers", []):
            tick_to_node.setdefault(t, n["id"])
    crowd_by = {n["id"]: float(n.get("crowdedness", 0.5)) for n in g["nodes"]}
    cluster_rows = OI.cluster_buys() + OI.officer_buys()
    time.sleep(0.5)
    by_node: dict[str, list[dict]] = {}
    for r in cluster_rows:
        nid = tick_to_node.get(r.get("ticker", ""))
        if nid:
            by_node.setdefault(nid, []).append(r)
    for nid, rs in by_node.items():
        rows.append(C.rule_insider_cluster(nid, rs))
    node_tickers = sorted(t for t in tick_to_node if t.isupper() and len(t) <= 6)
    for t, s in FIN.daily_short(node_tickers).items():
        rows.append(C.rule_short_crowded(
            tick_to_node.get(t, t), s.get("short_ratio"),
            crowd_by.get(tick_to_node.get(t, t), 0.0)))

    rows.extend(lab_rows[:8])
    ranked = C.rank(rows)
    _CONNECT_RENDER = "## Connections\n\n" + C.render(ranked)
    return f"{len(ranked)} connections ({len(mani)} manifold reads)"


if __name__ == "__main__":
    raise SystemExit(main())
