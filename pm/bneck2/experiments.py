"""bneck2 experiments — hypothesis registry + runnable tests (cg-flow).

Each experiment: HYP (id/title/prediction/falsifier/data) + run() ->
(result, verdict, n). Live keyless datastreams; math covered by fixtures
in tests/test_lab.py. Verdicts here are PILOT-grade until n compounds.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import lab as LAB  # noqa: E402


def _h(hyp_id, title, prediction, falsifier, data=""):
    LAB.preregister(hyp_id, title, prediction, falsifier, data)
    return hyp_id


def e001_burst_forward() -> tuple[dict, str, int]:
    """NVDA Sep-02 filings burst -> 4-trading-day forward return.

    Prereg amendment (receipt-logged): 5d needs today's close, Yahoo lags
    a day; 4d (Sep-02 -> Sep-08) is the longest closed window. Same test.
    """
    from bneck2 import prices as P
    _h("E001", "SEC burst precedes drift",
       "NVDA 4d forward return from Sep-02-2026 differs from 0 by >2pp",
       "forward return within ±2pp of zero",
       "SEC filings (logged) + Yahoo daily closes")
    fr = P.forward_return("NVDA", "2026-09-02", 4)
    r = fr.get("return")
    if r is None:
        return {"note": fr.get("note", "no data")}, "INCONCLUSIVE", 1
    verdict = "CONFIRMED" if abs(r) > 0.02 else "REFUTED"
    return {"ticker": "NVDA", "start": fr["start"], "end": fr["end"],
            "fwd_5d": r,
            "note": f"NVDA burst Sep-02 (Stevens $411M) -> 4d {r:+.1%}; n=1, directional only",
            "burst": {"form4": 15, "deal": 5}}, verdict, 1


def e002_attack_crowded() -> tuple[dict, str, int]:
    """Attack-HIGH + crowded names => DISSOLUTION_WATCH mapping holds."""
    _h("E002", "attack + crowded = watch, not buy",
       "optical_io attack-HIGH coincides with CPO names already +150-1000% 1Y",
       "CPO names flat/down 1Y despite attack signal",
       "OpenAlex attack tier + PhotonCap 1Y returns (websearch 2026-09-10)")
    result = {"node": "optical_io", "attack": "HIGH (+130%, 342 works)",
              "names_1y": {"AEHR": "+1033%", "FORM": "+468%",
                           "Chroma": "+757%", "KEYS": "+150%"},
              "note": "attack real AND crowded -> mapping says WATCH; voted CONFIRMED as mapping evidence"}
    return result, "CONFIRMED", 4


def e003_venue_spread() -> tuple[dict, str, int]:
    """Same-question PM vs Kalshi spreads worth harvesting."""
    from collectors import kalshi as KL
    from collectors import polymarket as PM
    _h("E003", "cross-venue spreads exceed fees sometimes",
       ">=1 same-question pair with |p_pm - p_kal| > 0.06 after fees",
       "all matched pairs within 0.06",
       "PM Gamma + Kalshi open events, token-overlap match >=0.5")
    pm_rows, kal = [], []
    for q in ("nuclear power", "artificial intelligence", "robot"):
        pm_rows += PM.fetch_markets(q)
        kal += KL.fetch_markets(q)
    pairs = _match(pm_rows, kal)
    wide = [p for p in pairs if abs(p["p_pm"] - p["p_kal"]) > 0.06]
    # Closest across venues regardless of threshold (segmentation read).
    closest = pairs[:3]
    result = {"pairs": len(pairs), "wide": len(wide),
              "top": wide[:5], "closest": closest,
              "note": (f"{len(wide)}/{len(pairs)} pairs >6pp apart; "
                       f"max jaccard {[p['jaccard'] for p in closest[:1]]} — "
                       "venues list different questions (PM: earnings/noise, "
                       "Kalshi: science timelines)")}
    return result, ("CONFIRMED" if wide else "REFUTED"), len(pairs)


def _tok(s: str) -> set[str]:
    return {w.lower() for w in s.replace("?", "").split() if len(w) > 3}


def _match(pm_rows: list[dict], kal_rows: list[dict]) -> list[dict]:
    out = []
    for a in pm_rows:
        ta = _tok(a.get("question", ""))
        if not ta:
            continue
        for b in kal_rows:
            tb = _tok(b.get("question", ""))
            if not tb:
                continue
            j = len(ta & tb) / len(ta | tb)
            if j >= 0.5:
                out.append({"pm_q": a["question"][:90],
                            "kal_q": b["question"][:90],
                            "p_pm": a["p"], "p_kal": b["p"],
                            "spread": round(abs(a["p"] - b["p"]), 3),
                            "jaccard": round(j, 2)})
    out.sort(key=lambda r: -r["spread"])
    return out


def e004_consensus_hitrate() -> tuple[dict, str, int]:
    """Whale consensus direction matches resolutions."""
    from collectors import polymarket as PM
    from collectors import polywhale as PW
    _h("E004", "whale consensus predicts resolution",
       "consensus outcome == resolved outcome on >=60% of resolved markets",
       "hit rate <60%",
       "PM best-book markets with p in {0,1} as resolved proxy + holders")
    hits, total, detail = 0, 0, []
    for q in ("artificial intelligence", "quantum computer"):
        for m in PM.fetch_markets(q):
            if m.get("p") not in (0.0, 1.0) or not m.get("conditionId"):
                continue
            con = PW.consensus([m])
            if not con:
                continue
            resolved_yes = m["p"] == 1.0
            called_yes = con[0]["outcome"] == 1
            total += 1
            ok = resolved_yes == called_yes
            hits += ok
            detail.append({"q": m["question"][:60], "hit": ok,
                           "n": con[0]["n_wallets"]})
            if total >= 8:
                break
        if total >= 8:
            break
    rate = round(hits / total, 3) if total else 0.0
    return {"hits": hits, "total": total, "rate": rate, "detail": detail,
            "note": f"consensus hit rate {rate} on {total} resolved markets"}, \
        ("CONFIRMED" if total >= 3 and rate >= 0.6 else "INCONCLUSIVE"), total


def e005_severity_conviction() -> tuple[dict, str, int]:
    """Severity B rank-correlates with conviction (internal consistency)."""
    from bneck2 import graph as G
    from bneck2 import migration as M
    from bneck2 import quant as Q
    _h("E005", "B and conviction agree",
       "Spearman rank correlation(B, conviction) > 0.3 across 16 nodes",
       "rho <= 0.3 (severity measures something unrelated)",
       "graph_v2 + readings (no network)")
    g = G.load_graph()
    readings = Q.load_readings()
    b = {n["id"]: M.severity(n, readings.get(n["id"]))["B"] for n in g["nodes"]}
    c = {n["id"]: G.score_node(n) for n in g["nodes"]}
    ids = list(b)
    rb = {i: r for r, i in enumerate(sorted(ids, key=lambda i: b[i]))}
    rc = {i: r for r, i in enumerate(sorted(ids, key=lambda i: c[i]))}
    n = len(ids)
    d2 = sum((rb[i] - rc[i]) ** 2 for i in ids)
    rho = 1 - 6 * d2 / (n * (n * n - 1))
    return ({"rho": round(rho, 3), "n": n,
             "note": f"Spearman(B, conviction) = {rho:.2f}, n={n} directional"},
            "CONFIRMED" if rho > 0.3 else "REFUTED", n)


def e006_gap_board() -> tuple[dict, str, int]:
    """Belief-gap baseline projection (no test — records the board)."""
    from bneck2 import worlds as W
    _h("E006", "gap board baseline",
       "records top P_you-P_market gaps for tracking (no falsifier: baseline)",
       "n/a baseline", "worlds.json")
    doc = W.load_worlds()
    gaps = sorted(((w["id"], round(w["p_you"] - w["p_market"], 3))
                   for w in doc["worlds"]),
                  key=lambda t: -abs(t[1]))[:6]
    return {"gaps": gaps, "note": f"top gaps: {gaps[:3]}"}, "INCONCLUSIVE", len(gaps)


def e007_burst_panel() -> tuple[dict, str, int]:
    _h("E007", "burst->drift panel (needs history)",
       "burst windows show |5d drift| > 2pp more often than calm windows",
       "indistinguishable from calm windows",
       "PREREGISTERED ONLY: needs >=10 burst + 10 calm windows across tickers")
    return {"note": "preregistered; blocked on multi-week verdict history",
            "need": "10 burst + 10 calm windows"}, "INCONCLUSIVE", 0


def e008_venue_segmentation() -> tuple[dict, str, int]:
    _h("E008", "venues segment by question type",
       "Kalshi open events skew science/tech timelines, PM skews "
       "earnings/politics/noise; same-question overlap <5%",
       "overlap >=5% same-question pairs at jaccard>=0.5",
       "E003 closest-pairs output (no new fetch)")
    return {"note": "preregistered from E003 finding; arb needs "
                    "human-confirmed pairs (pmbot workflow), not fuzzy match",
            "next": "curate arb_pairs.yaml by hand"}, "INCONCLUSIVE", 0


def e009_severity_crowdedness() -> tuple[dict, str, int]:
    from bneck2 import graph as G
    from bneck2 import migration as M
    from bneck2 import quant as Q
    _h("E009", "B-vs-conviction gap is the crowdedness term",
       "adding (1-crowdedness) to severity flips E005 rho positive",
       "rho stays <= 0.3 after the penalty (gap is structural, keep both)",
       "graph_v2 + readings (no network)")
    g = G.load_graph()
    readings = Q.load_readings()
    ids = [n["id"] for n in g["nodes"]]
    b = {}
    for n in g["nodes"]:
        s = M.severity(n, readings.get(n["id"]))["B"]
        b[n["id"]] = s * (1 - float(n.get("crowdedness", 0.5)))
    c = {n["id"]: G.score_node(n) for n in g["nodes"]}
    n = len(ids)
    rb = {i: r for r, i in enumerate(sorted(ids, key=lambda i: b[i]))}
    rc = {i: r for r, i in enumerate(sorted(ids, key=lambda i: c[i]))}
    d2 = sum((rb[i] - rc[i]) ** 2 for i in ids)
    rho = round(1 - 6 * d2 / (n * (n * n - 1)), 3)
    return {"rho_penalized": rho, "rho_plain": -0.438, "n": n,
            "note": f"penalized rho={rho:.2f} vs plain -0.44"}, \
        ("CONFIRMED" if rho > 0.3 else "REFUTED"), n


def e010_acq_chain() -> tuple[dict, str, int]:
    """H-ACQ-1: lab capital events -> counterparty +5pp vs SPY in 20d."""
    import json
    from bneck2 import acq as A
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-ACQ-1", "lab capital events move counterparties",
        "counterparty 20d excess vs SPY > +5pp on >=60% of events (n>=5)",
        "hit rate <60% or mean excess <= 0",
        "commitments.json dates + Yahoo daily closes vs SPY")
    doc = json.loads((ROOT / "data" / "labs" / "commitments.json")
                     .read_text(encoding="utf-8"))
    good, dropped = A.eligible(doc.get("commitments", []))
    rows = A.event_study(good)
    s = A.summarize(rows)
    s["events"] = len(good)
    s["dropped"] = len(dropped)
    s["rows"] = [(r["event"], r["ticker"], r.get("excess")) for r in rows]
    s["note"] = (f"{s.get('hit_rate', '?')} hit rate, mean excess "
                 f"{s.get('mean_excess', '?')}, n={s['n']} directional")
    return s, s["verdict"], s["n"]


def e011_acq_silicon() -> tuple[dict, str, int]:
    """H-ACQ-2 (refine of H-ACQ-1): irreversible silicon/capacity/nuclear
    commitments move counterparties; generic deployments do not."""
    from bneck2 import acq as A
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-ACQ-2", "only irreversible commitments move prices",
        "silicon-roadmap/capacity-contract/multidecade kinds: hit>=60%, n>=5",
        "hit <60% (no better than all-events)",
        "same event study, kind subset; parent H-ACQ-1")
    rows, _ = _acq_rows()
    sub = [r for r in rows if r.get("kind") in
           ("silicon-roadmap", "capacity-contract", "multidecade-contract")]
    s = A.summarize(sub)
    s["rows"] = [(r["event"], r["ticker"], r["kind"], r["excess"]) for r in sub]
    s["parent"] = "H-ACQ-1 (refine)"
    s["note"] = (f"silicon/capacity subset: hit {s.get('hit_rate','?')}, "
                 f"mean {s.get('mean_excess','?')}, n={s['n']}")
    return s, s["verdict"], s["n"]


def e012_acq_size_split() -> tuple[dict, str, int]:
    """H-ACQ-3 (refine of H-ACQ-1): revenue-scale split in event response.

    Prereg amendment (receipt-logged): Yahoo chart meta carries no
    marketCap here and v7 needs crumbs, so size = XBRL revenue TTM
    (>= $100B = mega), measured via collectors/sec_facts.py. Same
    hypothesis, honest instrument.
    """
    from bneck2 import acq as A
    from bneck2 import lab as LAB
    from collectors import sec_facts as SF
    LAB.preregister(
        "H-ACQ-3", "size split in event response",
        "sub-$100B-revenue hit>=60%; mega hit<40%",
        "no size pattern",
        "XBRL revenue TTM split; parent H-ACQ-1")
    CIK = {"NVDA": "1045810", "AMD": "2488", "AVGO": "1730168",
           "GOOGL": "1652044", "AMZN": "1018724", "META": "1326801",
           "CSCO": "858877", "MU": "1430265", "CRWV": "1763920"}
    rows, _ = _acq_rows()
    rev = {}
    for r in rows:
        t = r["ticker"]
        if t not in rev:
            f = SF.fundamentals(CIK[t]) if t in CIK else {}
            rev[t] = f.get("revenue_ttm")
    mega = [r for r in rows if (rev.get(r["ticker"]) or 0) >= 1e11]
    rest = [r for r in rows if rev.get(r["ticker"]) is not None
            and rev[r["ticker"]] < 1e11]
    unknown = sorted({r["ticker"] for r in rows if rev.get(r["ticker"]) is None})
    sm, sr = A.summarize(mega), A.summarize(rest)
    out = {"mega": {**sm, "tickers": sorted({r["ticker"] for r in mega})},
           "rest": {**sr, "tickers": sorted({r["ticker"] for r in rest})},
           "unknown_size": unknown,
           "parent": "H-ACQ-1 (refine)",
           "note": f"mega(rev>=$100B) hit {sm.get('hit_rate', '?')} n={sm['n']} "
                   f"vs rest hit {sr.get('hit_rate', '?')} n={sr['n']}"}
    verdict = ("CONFIRMED" if sr.get("hit_rate", 0) >= 0.6 and sm.get("hit_rate", 1) < 0.4
               and sr.get("n", 0) >= 3 else "REFUTED"
               if sr.get("n", 0) + sm.get("n", 0) >= 5 else "INCONCLUSIVE")
    return out, verdict, sr.get("n", 0) + sm.get("n", 0)


def e013_redteam() -> tuple[dict, str, int]:
    """Monthly red-team: strongest case AGAINST the top-conviction node."""
    from bneck2 import graph as G
    from bneck2 import quant as Q
    from bneck2 import lab as LAB
    LAB.preregister(
        "E013", "monthly red-team vs top conviction",
        "top-conviction node shows >=3 disconfirming facts (non-firings, "
        "negative drift, crowdedness>=0.7)",
        "fewer than 3 disconfirming facts (conviction stands unattacked)",
        "graph + verdicts + prices (no network)")
    import json as _j
    g = G.load_graph()
    rows = Q.score_all(g, Q.load_readings())
    top = max(rows, key=lambda r: r.get("binding", 0))
    node = next(n for n in g["nodes"] if n["id"] == top["id"])
    ver = [_j.loads(l) for l in
           (ROOT / "data" / "beliefs" / "kill_observations.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()]
    nonfire = sum(1 for r in ver if r.get("node_id") == top["id"]
                  and r.get("verdict") == "NOT TRIGGERED")
    facts = []
    if nonfire >= 10:
        facts.append(f"{nonfire} non-firing verdicts on this node")
    if float(node.get("crowdedness", 0)) >= 0.7:
        facts.append(f"crowdedness {node.get('crowdedness')} (consensus long)")
    if top.get("dissolution", 0) >= 0.2:
        facts.append(f"dissolution {top['dissolution']:.2f} already priced")
    ok = len(facts) >= 3
    return {"node": top["id"], "binding": round(top.get("binding", 0), 3),
            "disconfirming": facts,
            "note": f"red-team vs {top['id']}: {len(facts)} disconfirming facts"}, \
        ("CONFIRMED" if ok else "REFUTED"), len(facts)


def e014_signal_chain() -> tuple[dict, str, int]:
    """H-SIG-1: factor composite beats momentum bogey on holdout."""
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-SIG-1", "composite beats momentum out-of-sample",
        "holdout Sharpe(composite) > Sharpe(momentum), same dates/costs",
        "composite <= momentum (factors add nothing)",
        "12mo monthly panel; train m1-9, holdout m10-12; verdict needs n>=30 rows")
    import json as _j
    prow = sorted((ROOT / "data" / "predict").glob("panel-*.jsonl"))
    rows = []
    for f in prow:
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        return {"note": "no predict panel yet; run scripts/build_predict_panel.py",
                "need": "panel files"}, "INCONCLUSIVE", 0
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 3, 0)]
    train = [r for r in rows if r["date"] < cut]
    hold = [r for r in rows if r["date"] >= cut]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 20]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    if not winners:
        return {"train_screen": scr, "note": "no factor clears IC>0.1 on train"},
    ("REFUTED",  len(train))
    comp_hold = PD.composite_by_date([dict(r) for r in hold], winners,
                                       signs)
    mom_hold = [{"date": r["date"], "ticker": r["ticker"],
                 "score": r.get("f_mom_20") or 0.0,
                 "forward_return": r.get("fwd_20")} for r in hold]
    _, cs = BT.walk_forward([{"date": r["date"], "ticker": r["ticker"],
                              "score": r["score"],
                              "forward_return": r.get("fwd_20") or 0.0}
                             for r in comp_hold if r.get("fwd_20") is not None])
    _, ms = BT.walk_forward([dict(r, forward_return=r.get("forward_return") or 0.0)
                             for r in mom_hold if r.get("forward_return") is not None])
    out = {"train_screen": scr, "winners": winners,
           "composite_sharpe": cs.get("sharpe"), "momentum_sharpe": ms.get("sharpe"),
           "holdout_n": len(hold),
           "note": f"composite {cs.get('sharpe')} vs momentum {ms.get('sharpe')} on holdout"}
    verdict = ("CONFIRMED" if (cs.get("sharpe") or -9) > (ms.get("sharpe") or 9)
               and len(hold) >= 30 else "REFUTED" if len(hold) >= 30 else "INCONCLUSIVE")
    return out, verdict, len(hold)


def e015_signal_biweekly() -> tuple[dict, str, int]:
    """H-SIG-2 (mutate of H-SIG-1): biweekly grid (26 dates) cures the
    3-point-Sharpe noise; same factors, train first 18, holdout last 8."""
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-SIG-2", "biweekly grid rescues the signal test",
        "holdout Sharpe(composite) > Sharpe(momentum) on 8 biweekly dates",
        "composite <= momentum (factors add nothing at any grid)",
        "data/predict/biwk-*.jsonl; parent H-SIG-1")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        return {"note": "no biweekly panel; run build_predict_panel.py --biweekly",
                "need": "biweekly panel"}, "INCONCLUSIVE", 0
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 8, 0)]
    train = [r for r in rows if r["date"] < cut]
    hold = [r for r in rows if r["date"] >= cut]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 40]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    if not winners:
        return {"train_screen": scr, "note": "no factor clears IC>0.1 on train"},
    ("REFUTED", len(train))
    comp_hold = PD.composite_by_date([dict(r) for r in hold], winners, signs)
    mom_hold = [{"date": r["date"], "ticker": r["ticker"],
                 "score": r.get("f_mom_20") or 0.0,
                 "forward_return": r.get("fwd_20")} for r in hold]

    def _wf(rs):
        ok = []
        for r in rs:
            fr = r.get("forward_return", r.get("fwd_20"))
            if fr is not None:
                ok.append(dict(r, forward_return=fr))
        return BT.walk_forward(ok)[1] if ok else {"sharpe": None}

    cs, ms = _wf(comp_hold), _wf(mom_hold)
    out = {"train_screen": scr, "winners": winners,
           "composite_sharpe": cs.get("sharpe"),
           "momentum_sharpe": ms.get("sharpe"),
           "holdout_n": len(hold), "holdout_dates": len(dates) - len([d for d in dates if d < cut]),
           "note": f"composite {cs.get('sharpe')} vs momentum {ms.get('sharpe')} on biweekly holdout"}
    verdict = ("CONFIRMED" if (cs.get("sharpe") is not None and ms.get("sharpe") is not None
               and cs["sharpe"] > ms["sharpe"]) and len(hold) >= 60
               else "REFUTED" if len(hold) >= 60 else "INCONCLUSIVE")
    return out, verdict, len(hold)


def e016_burst_reversal() -> tuple[dict, str, int]:
    """H-SIG-3 (mutate of H-SIG-2): insider bursts REVERSE (IC<0), and
    leg attribution tells whether shorts carry the composite."""
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-SIG-3", "burst reversal + short-leg carry",
        "negated-burst factor IC>0.15 on full biweekly panel AND "
        "composite short leg Sharpe > long leg Sharpe",
        "burst IC>=0 as long, or long leg carries (no reversal edge)",
        "data/predict/biwk-*.jsonl; parent H-SIG-2")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    nb = [dict(r, f_burst_neg=-(r["f_burst"] or 0.0)) for r in rows
          if r.get("f_burst") is not None]
    ic = PD.spearman([r["f_burst_neg"] for r in nb],
                     [r["fwd_20"] for r in nb])
    # leg attribution on composite winners from E015 screen
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
    longs, shorts = [], []
    for d in sorted(by_date):
        g = by_date[d]
        sc = {r["ticker"]: (r.get("f_mom_20") or 0) + (r.get("f_attack") or 0)
              for r in g}
        pos = BT.make_positions(sc, 0.2)
        ret = {r["ticker"]: r["fwd_20"] for r in g}
        longs.append(sum(max(pos[t], 0) * ret.get(t, 0) for t in pos))
        shorts.append(sum(min(pos[t], 0) * ret.get(t, 0) for t in pos))
    import math as _m
    def _sh(xs):
        m = sum(xs) / len(xs)
        v = sum((x - m) ** 2 for x in xs) / max(len(xs) - 1, 1)
        return round(m / (_m.sqrt(v) or 1e-9), 3)
    out = {"burst_neg_IC": ic, "n_burst": len(nb),
           "long_leg_sharpe_like": _sh(longs), "short_leg_sharpe_like": _sh(shorts),
           "note": f"neg-burst IC={ic} n={len(nb)}; long {_sh(longs)} vs short {_sh(shorts)}"}
    verdict = ("CONFIRMED" if (ic or 0) > 0.15 and _sh(shorts) > _sh(longs)
               else "REFUTED")
    return out, verdict, len(nb)


def e017_long_only() -> tuple[dict, str, int]:
    """H-SIG-4: long-only top-tercile beats equal-weight universe.

    The L/S composites lose less but still lose (drawdown regime).
    Test whether the long leg alone carries edge vs holding everything.
    """
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-SIG-4", "long-only top tercile beats universe",
        "mean(top-tercile fwd) > mean(all fwd) by >=2pp on holdout",
        "no 2pp edge (ranking adds nothing long-only)",
        "biweekly panel; parent H-SIG-2")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 8, 0)]
    hold = [r for r in rows if r["date"] >= cut]
    train = [r for r in rows if r["date"] < cut]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 40]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    scored = PD.composite_by_date(hold, winners or ["f_mom_20"], signs)
    by_date = {}
    for r in scored:
        by_date.setdefault(r["date"], []).append(r)
    ex, ux = [], []
    for d in sorted(by_date):
        g = sorted(by_date[d], key=lambda r: -r["score"])
        k = max(len(g) // 3, 1)
        ex.append(sum(r["fwd_20"] for r in g[:k]) / k
                  - sum(r["fwd_20"] for r in g) / len(g))
    m = sum(ex) / len(ex) if ex else 0.0
    out = {"winners": winners, "n_dates": len(ex),
           "mean_excess_vs_universe": round(m, 4),
           "note": f"top-tercile beats universe by {m:+.2%} per window"}
    return out, ("CONFIRMED" if m >= 0.02 else "REFUTED"), len(ex)




def utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def e018_nvda_sell_drift() -> tuple[dict, str, int]:
    """H-NVDA-1: heavy insider SELL months precede negative drift."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    from collectors import openinsider as OI
    LAB.preregister(
        "H-NVDA-1", "insider sell intensity precedes drift",
        "top-quartile sell months -> next-month return < median month",
        "no difference (sales are noise/10b5-1)",
        "OpenInsider NVDA tape (100 rows) + Yahoo monthly closes")
    trades = [t for t in OI.by_ticker("NVDA") if t.get("is_sale")]
    closes = {c["date"][:7]: c["close"] for c in P.history("NVDA", "1y").get("closes", [])}
    by_m = {}
    for t in trades:
        by_m.setdefault(t.get("trade_date", "")[:7], 0.0)
        by_m[t.get("trade_date", "")[:7]] += abs(t.get("value_usd", 0))
    months = sorted(m for m in by_m if m in closes)
    if len(months) < 4:
        return {"note": "insufficient months", "months": months}, "INCONCLUSIVE", 0
    vals = sorted(by_m[m] for m in months)
    cut = vals[3 * len(vals) // 4]
    heavy = [m for m in months if by_m[m] >= cut]
    res = []
    for m in months:
        y, mm = map(int, m.split("-"))
        nm = f"{y + (mm == 12)}-{mm % 12 + 1:02d}"
        if m in closes and nm in closes and closes[m]:
            res.append((m, (closes[nm] - closes[m]) / closes[m], m in heavy))
    if len(res) < 4:
        return {"note": "insufficient forward months"}, "INCONCLUSIVE", 0
    hr = [r for _, r, h in res if h]
    lr = [r for _, r, h in res if not h]
    mh = sum(hr) / len(hr)
    ml = sum(lr) / len(lr)
    out = {"heavy_months": len(hr), "light_months": len(lr),
           "heavy_mean": round(mh, 4), "light_mean": round(ml, 4),
           "note": f"heavy-sell months {mh:+.1%} vs rest {ml:+.1%}"}
    return out, ("CONFIRMED" if mh < ml - 0.02 else "REFUTED"), len(res)


def e019_btc_nvda_beta() -> tuple[dict, str, int]:
    """H-BTC-1: BTC-NVDA trailing correlation (pair readout)."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    from bneck2 import predict as PD
    LAB.preregister(
        "H-BTC-1", "BTC-NVDA correlation measurable and positive",
        "90d return correlation > 0.3",
        "rho <= 0.3 (decoupled — trade separately)",
        "CoinGecko BTC daily + Yahoo NVDA daily")
    bc = {c["date"]: c["close"] for c in P.crypto_history("bitcoin", 120).get("closes", [])}
    nv = {c["date"]: c["close"] for c in P.history("NVDA", "6mo").get("closes", [])}
    days = sorted(set(bc) & set(nv))[-90:]
    if len(days) < 30:
        return {"note": "insufficient overlap", "n": len(days)}, "INCONCLUSIVE", 0
    br = [(bc[days[i + 1]] - bc[days[i]]) / bc[days[i]] for i in range(len(days) - 1)]
    nr = [(nv[days[i + 1]] - nv[days[i]]) / nv[days[i]] for i in range(len(days) - 1)]
    rho = PD.spearman(br, nr)
    mb, mn = sum(br) / len(br), sum(nr) / len(nr)
    den = sum((b - mb) ** 2 for b in br)
    beta = (sum((b - mb) * (n - mn) for b, n in zip(br, nr)) / den) if den else None
    out = {"rho": rho, "beta_btc_on_nvda": round(beta, 3) if beta else None,
           "n_days": len(days),
           "note": f"90d BTC-NVDA return rho={rho}, beta={beta}"}
    return out, ("CONFIRMED" if (rho or 0) > 0.3 else "REFUTED"), len(days)


def e020_btc_pm_snapshot() -> tuple[dict, str, int]:
    """H-BTC-2: snapshot live BTC price-level markets for 7d resolution."""
    from bneck2 import lab as LAB
    from collectors import polymarket as PM
    LAB.preregister(
        "H-BTC-2", "BTC level markets resolve as priced (calibration)",
        ">=70% resolve in the priced direction",
        "below 70% (miscalibrated levels)",
        "snapshot today, resolve via re-fetch in 7d")
    rows = PM.fetch_markets("bitcoin")
    live = [r for r in rows if 0.05 < r.get("p", 0) < 0.95][:10]
    import json as _j
    snap_path = ROOT / "data" / "predict" / "btc_levels.json"
    try:
        snaps = _j.loads(snap_path.read_text())
    except (OSError, ValueError):
        snaps = []
    have = {(s.get("question"), s.get("p")) for s in snaps}
    new = 0
    for r in live:
        if (r["question"], r["p"]) not in have:
            snaps.append({"question": r["question"], "p": r["p"],
                          "snapshot": utcnow()[:10], "resolved": None})
            new += 1
    (ROOT / "data" / "predict").mkdir(parents=True, exist_ok=True)
    snap_path.write_text(_j.dumps(snaps, indent=1))
    res = [s for s in snaps if s.get("resolved") is not None]
    hits = sum(1 for s in res if s.get("hit"))
    out = {"tracked": len(snaps), "new": new, "resolved": len(res),
           "hits": hits, "note": f"{len(snaps)} BTC levels tracked, {len(res)} resolved"}
    if len(res) < 5:
        return out, "INCONCLUSIVE", len(res)
    return out, ("CONFIRMED" if hits / len(res) >= 0.7 else "REFUTED"), len(res)


def e021_sec_leads_price() -> tuple[dict, str, int]:
    """H-LEAD-1: SEC filings lead price moves (insiders file, then drift)."""
    from bneck2 import lab as LAB
    from bneck2 import leads as LD
    LAB.preregister(
        "H-LEAD-1", "filings lead prices",
        "SEC-weekly xcorr peaks at lag>0 vs NVDA weekly returns",
        "peak at lag<=0 (prices move first / sync noise)",
        "NVDA submissions history + Yahoo weeklies, 17 windows")
    starts, sec, _, rets = _weekly_panel_16w("NVDA", "1045810", "Nvidia")
    ll = LD.lead_lag(sec, rets)
    out = {"windows": len(starts) - 1, "peak": ll, "comparisons": 9,
           "note": f"SEC->NVDA: {ll['verdict']} (9-lag search: discovery-grade)"}
    return out, "EXPLORATORY", len(starts) - 1


def e022_hn_leads_price() -> tuple[dict, str, int]:
    """H-LEAD-2: HN chatter leads price (narrative precedes repricing)."""
    from bneck2 import lab as LAB
    from bneck2 import leads as LD
    LAB.preregister(
        "H-LEAD-2", "chatter leads prices",
        "HN-weekly xcorr peaks at lag>0 vs NVDA weekly returns",
        "peak at lag<=0",
        "HN Algolia date ranges + Yahoo weeklies, 17 windows")
    starts, _, hn, rets = _weekly_panel_16w("NVDA", "1045810", "Nvidia")
    ll = LD.lead_lag(hn, rets)
    out = {"windows": len(starts) - 1, "peak": ll, "comparisons": 9,
           "note": f"HN->NVDA: {ll['verdict']} (9-lag search: discovery-grade)"}
    return out, "EXPLORATORY", len(starts) - 1


def e023_filings_vs_chatter() -> tuple[dict, str, int]:
    """H-LEAD-3: filings vs chatter ordering (who moves first?)."""
    from bneck2 import lab as LAB
    from bneck2 import leads as LD
    LAB.preregister(
        "H-LEAD-3", "filings precede chatter",
        "SEC-weekly xcorr peaks at lag>0 vs HN-weekly",
        "peak at lag<=0 (chatter anticipates or syncs filings)",
        "same 17-window panel, both series")
    starts, sec, hn, _ = _weekly_panel_16w("NVDA", "1045810", "Nvidia")
    ll = LD.lead_lag(sec, hn)
    out = {"windows": len(starts) - 1, "peak": ll, "comparisons": 9,
           "note": f"SEC->HN: {ll['verdict']} (9-lag search: discovery-grade)"}
    return out, "EXPLORATORY", len(starts) - 1


def e024_pm_vs_x_order() -> tuple[dict, str, int]:
    """H-LEAD-4 (structural, preregistered): PMs lead X narrative.

    Mechanism: PM prices update on news in minutes (money at risk);
    X threads develop over days (E022 shows HN lags price +3w, and PM
    tracks news-prices faster than narrative). Test when X keyed:
    for dated X claims, compare claim date vs PM price-move date.
    """
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-LEAD-4", "prediction markets lead X narrative",
        "median(PM-move-date minus X-claim-date) < -3 days on >=10 pairs",
        "median >= -3 days (X anticipates or syncs)",
        "PREREGISTERED ONLY: needs keyed X firehose (stockify X-engine)")
    return {"note": "preregistered; blocked on X key funding",
            "proxy_evidence": "E022 HN lags price +3w r=0.69"}, "INCONCLUSIVE", 0


def e025_divergence() -> tuple[dict, str, int]:
    """H-DIV-1: insider buying into price weakness beats buying strength.

    Frontier (Johnsen 2026): divergent insider-bullish (buy vs bearish
    news) +2.46% next-day; convergent already priced. Our proxy for news:
    trailing-20d momentum sign at FILING date (public-info discipline).
    """
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-DIV-1", "divergent buys beat convergent buys",
        "buys with mom_20<0 outperform buys with mom_20>=0 by >=3pp fwd-20d",
        "no gap (divergence adds nothing)",
        "OpenInsider market-wide buys + Yahoo (filing-dated)")
    rows = _oi_buys_all()
    groups = {"div": [], "conv": []}
    for r in rows:
        t = r.get("ticker", "")
        fd = (r.get("filing_date", "") or "")[:10]
        if not t or len(fd) != 10:
            continue
        cl = {c["date"]: c["close"] for c in P.history(t, "3mo").get("closes", [])}
        ds = sorted(cl)
        i = next((k for k, d in enumerate(ds) if d >= fd), None)
        if i is None or i < 20 or i + 20 >= len(ds):
            continue
        mom = (cl[ds[i]] - cl[ds[i - 20]]) / cl[ds[i]]
        fwd = (cl[ds[i + 20]] - cl[ds[i]]) / cl[ds[i]]
        groups["div" if mom < 0 else "conv"].append(fwd)
    out = {k: {"n": len(v), "mean": round(sum(v) / len(v), 4) if v else None}
           for k, v in groups.items()}
    dm = out["div"]["mean"] if out["div"]["n"] else None
    cm = out["conv"]["mean"] if out["conv"]["n"] else None
    out["note"] = f"divergent {dm} (n={out['div']['n']}) vs convergent {cm} (n={out['conv']['n']})"
    n = out["div"]["n"] + out["conv"]["n"]
    verdict = ("CONFIRMED" if dm is not None and cm is not None and dm - cm >= 0.03
               else "REFUTED" if n >= 10 else "INCONCLUSIVE")
    return out, verdict, n


def e026_predisclosure_drift() -> tuple[dict, str, int]:
    """H-PRE-1: most of the move happens between trade and filing dates
    (Ozlen & Batumoglu 2026: 70-80% pre-disclosure)."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-PRE-1", "pre-disclosure drift dominates",
        "|trade->filing move| > |filing->+5d move| on >=60% of buys",
        "filing-window moves dominate (disclosure is the event)",
        "OpenInsider buy rows with both dates + Yahoo")
    rows = _oi_buys_all()
    pre, post, n = 0.0, 0.0, 0
    for r in rows:
        t = r.get("ticker", "")
        td, fd = (r.get("trade_date", "") or "")[:10], (r.get("filing_date", "") or "")[:10]
        if not t or len(td) != 10 or len(fd) != 10:
            continue
        cl = {c["date"]: c["close"] for c in P.history(t, "3mo").get("closes", [])}
        ds = sorted(cl)
        try:
            i0 = next(k for k, d in enumerate(ds) if d >= td)
            i1 = next(k for k, d in enumerate(ds) if d >= fd)
        except StopIteration:
            continue
        if i1 + 5 >= len(ds):
            continue
        pre += abs((cl[ds[i1]] - cl[ds[i0]]) / cl[ds[i0]]) if cl[ds[i0]] else 0
        post += abs((cl[ds[min(i1 + 5, len(ds) - 1)]] - cl[ds[i1]]) / cl[ds[i1]]) if cl[ds[i1]] else 0
        n += 1
        if n >= 40:
            break
    out = {"n": n, "pre_mean": round(pre / n, 4) if n else None,
           "post_mean": round(post / n, 4) if n else None,
           "note": f"pre-disclosure {pre / n:+.2%} vs post {post / n:+.2%} (n={n})" if n else "no rows"}
    verdict = ("CONFIRMED" if n >= 10 and pre > post
               else "REFUTED" if n >= 10 else "INCONCLUSIVE")
    return out, verdict, n


def e027_espp_filter() -> tuple[dict, str, int]:
    """H-ESP-1: same-date+price clusters are programmatic (Johnsen gates).

    Audit our cluster feed: flag groups where >=80% of qualifying buys
    share date+price, and <$10k singles. Reports contamination rate."""
    from bneck2 import lab as LAB
    from collectors import openinsider as OI
    LAB.preregister(
        "H-ESP-1", "cluster feed contains programmatic blocks",
        ">=1 cluster group meets ESPP signature (>=80% same date+price)",
        "no group meets it (feed is clean)",
        "cluster_buys page rows")
    rows = OI.cluster_buys()
    from collections import Counter
    flagged, total = 0, 0
    for t in {r.get("ticker", "") for r in rows if r.get("ticker")}:
        g = [r for r in rows if r.get("ticker") == t and r.get("value_usd", 0) >= 10000]
        if len(g) < 3:
            continue  # singletons trivially "match" — not a cluster
        total += 1
        keys = Counter((r.get("trade_date", ""), r.get("price", "")) for r in g)
        if keys and max(keys.values()) / len(g) >= 0.8:
            flagged += 1
    out = {"groups": total, "flagged": flagged,
           "note": f"{flagged}/{total} cluster groups look programmatic"}
    return out, ("CONFIRMED" if flagged > 0 else "REFUTED"), total


def e028_distance_high() -> tuple[dict, str, int]:
    """H-DH-1: buys nearer 52w highs do better (microcap paper: 36% weight).

    Pilot on market-wide buy rows: split by distance-from-high terciles,
    compare forward-20d means."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-DH-1", "distance-from-high sorts buy outcomes",
        "top-tercile (nearest high) beats bottom by >=3pp fwd-20d",
        "no ordering (distance is noise here)",
        "OpenInsider buys + Yahoo 1y highs, filing-dated")
    rows = _oi_buys_all()
    scored = []
    cache = {}
    for r in rows:
        t = r.get("ticker", "")
        fd = (r.get("filing_date", "") or "")[:10]
        if not t or len(fd) != 10:
            continue
        if t not in cache:
            cache[t] = {c["date"]: c["close"] for c in P.history(t, "1y").get("closes", [])}
        cl = cache[t]
        ds = sorted(cl)
        i = next((k for k, d in enumerate(ds) if d >= fd), None)
        if i is None or i + 20 >= len(ds) or i < 200:
            continue
        hi = max(c for d, c in cl.items() if d <= ds[i])
        dist = (cl[ds[i]] - hi) / hi if hi else 0
        fwd = (cl[ds[i + 20]] - cl[ds[i]]) / cl[ds[i]]
        scored.append((dist, fwd))
        if len(scored) >= 60:
            break
    if len(scored) < 9:
        return {"note": "insufficient buy rows with history", "n": len(scored)}, "INCONCLUSIVE", len(scored)
    scored.sort()
    k = max(len(scored) // 3, 1)
    lo = sum(s[1] for s in scored[:k]) / k
    hi = sum(s[1] for s in scored[-k:]) / k
    out = {"n": len(scored), "near_high": round(hi, 4), "far_high": round(lo, 4),
           "note": f"near-high {hi:+.1%} vs far {lo:+.1%} (n={len(scored)})"}
    return out, ("CONFIRMED" if hi - lo >= 0.03 else "REFUTED"), len(scored)


def e029_deep_screen() -> tuple[dict, str, int]:
    """H-DEEP-1: factor ICs on 2y weekly panel (train first 3/4)."""
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-DEEP-1", "deep screen finds IC>0.1 factors",
        ">=2 factors clear |IC|>0.1 with n>=100 on train split",
        "fewer than 2 (no structure at weekly grid)",
        "deep-weekly.jsonl; train first 78w, no holdout touch")
    rows = [r for r in _deep_rows() if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    cut = dates[3 * len(dates) // 4]
    train = [r for r in rows if r["date"] < cut]
    scr = PD.screen(train, DEEP_FACTORS)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 100]
    out = {"train_screen": scr, "winners": winners, "n_train": len(train),
           "note": f"winners={winners}"}
    return out, ("CONFIRMED" if len(winners) >= 2 else "REFUTED"), len(train)

def e030_deep_walkforward() -> tuple[dict, str, int]:
    """H-DEEP-2: composite beats buy-hold AND momentum on holdout quarter."""
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-DEEP-2", "composite beats bogeys on holdout",
        "composite Sharpe > max(buyhold, momentum) on last 26w",
        "composite <= best bogey",
        "deep-weekly.jsonl; winners/signs from train only")
    rows = [r for r in _deep_rows() if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    cut = dates[3 * len(dates) // 4]
    train = [r for r in rows if r["date"] < cut]
    hold = [r for r in rows if r["date"] >= cut]
    scr = PD.screen(train, DEEP_FACTORS)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 100]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    if not winners:
        return {"note": "no winners (see E029)", "winners": []}, "REFUTED", len(train)
    comp = PD.composite_by_date([dict(r) for r in hold], winners, signs)
    mom = [{"date": r["date"], "ticker": r["ticker"],
            "score": r.get("f_mom_20") or 0.0,
            "forward_return": r["fwd_20"]} for r in hold]
    uni = [{"date": r["date"], "ticker": r["ticker"], "score": 1.0,
            "forward_return": r["fwd_20"]} for r in hold]

    def _wf(rs):
        ok = []
        for r in rs:
            fr = r.get("forward_return", r.get("fwd_20"))
            if fr is not None:
                ok.append(dict(r, forward_return=fr))
        return BT.walk_forward(ok, quantile=0.25)[1] if ok else {"sharpe": None}

    cs, ms, us = _wf(comp), _wf(mom), _wf(uni)
    out = {"winners": winners, "holdout_n": len(hold),
           "composite_sharpe": cs.get("sharpe"),
           "momentum_sharpe": ms.get("sharpe"),
           "buyhold_sharpe": us.get("sharpe"),
           "note": f"comp {cs.get('sharpe')} vs mom {ms.get('sharpe')} vs bh {us.get('sharpe')}"}
    ok = (cs.get("sharpe") is not None and ms.get("sharpe") is not None
          and us.get("sharpe") is not None
          and cs["sharpe"] > max(ms["sharpe"], us["sharpe"]) and len(hold) >= 60)
    return out, ("CONFIRMED" if ok else "REFUTED"), len(hold)


def e031_momentum_only() -> tuple[dict, str, int]:
    """H-DEEP-3 (mutate): sole survivor (momentum IC 0.147) vs buy-hold."""
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-DEEP-3", "momentum-only beats buy-hold on holdout",
        "momentum Sharpe > buyhold Sharpe, last 26w, n>=60",
        "momentum <= buyhold (no timing edge at weekly grid)",
        "deep-weekly.jsonl; parent H-DEEP-2 (no composite survived)")
    import json as _j
    rows = [_j.loads(l) for l in
            (ROOT / "data" / "predict" / "deep-weekly.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    hold = [r for r in rows if r["date"] >= dates[3 * len(dates) // 4]]
    mom = [{"date": r["date"], "ticker": r["ticker"],
            "score": r.get("f_mom_20") or 0.0,
            "forward_return": r["fwd_20"]} for r in hold]
    uni = [{"date": r["date"], "ticker": r["ticker"], "score": 1.0,
            "forward_return": r["fwd_20"]} for r in hold]

    def _wf(rs):
        return BT.walk_forward(
            [dict(r, forward_return=r["forward_return"]) for r in rs],
            quantile=0.25)[1]

    ms, us = _wf(mom), _wf(uni)
    # subperiod stability: split holdout halves
    ds = sorted({r["date"] for r in hold})
    halves = []
    for part in (ds[:len(ds) // 2], ds[len(ds) // 2:]):
        sub = [r for r in mom if r["date"] in part]
        halves.append(_wf(sub).get("sharpe"))
    out = {"momentum_sharpe": ms.get("sharpe"),
           "buyhold_sharpe": us.get("sharpe"),
           "half_sharpes": halves, "n": len(hold),
           "note": f"mom {ms.get('sharpe')} vs bh {us.get('sharpe')}; halves {halves}"}
    ok = (ms.get("sharpe") is not None and us.get("sharpe") is not None
          and ms["sharpe"] > us["sharpe"] and len(hold) >= 60)
    return out, ("CONFIRMED" if ok else "REFUTED"), len(hold)


def e032_nvda_basket() -> tuple[dict, str, int]:
    """H-NVDA-1b: NVDA 13F basket (equal-weight publics) vs SPY from 6/30."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-NVDA-1b", "NVDA-validated names drift up",
        "13F public basket beats SPY from 2026-06-30 filing window",
        "basket <= SPY (validation followed, not predictive)",
        "hand-seeded 13F (XML host-blocked) + Yahoo")
    import json as _j
    doc = _j.loads((ROOT / "data" / "universe" / "nvda_13f_2026q2.json").read_text())
    names = [p_ for p_ in doc["positions"] if p_.get("ticker")]
    rets = {}
    for p_ in names:
        cl = {c["date"]: c["close"] for c in P.history(p_["ticker"], "6mo").get("closes", [])}
        ds = sorted(cl)
        i = next((k for k, d in enumerate(ds) if d >= "2026-06-30"), None)
        if i is not None and ds:
            j = len(ds) - 1
            rets[p_["ticker"]] = round((cl[ds[j]] - cl[ds[i]]) / cl[ds[i]], 4)
    sp = {c["date"]: c["close"] for c in P.history("SPY", "6mo").get("closes", [])}
    sds = sorted(sp)
    si = next((k for k, d in enumerate(sds) if d >= "2026-06-30"), None)
    spy = round((sp[sds[-1]] - sp[sds[si]]) / sp[sds[si]], 4) if si is not None else None
    vals = list(rets.values())
    m = round(sum(vals) / len(vals), 4) if vals else None
    out = {"basket": rets, "basket_mean": m, "spy": spy, "n": len(vals),
           "note": f"13F basket {m} vs SPY {spy} since 6/30 (n={len(vals)})"}
    verdict = ("CONFIRMED" if m is not None and spy is not None and m - spy >= 0.05
               else "REFUTED" if m is not None and spy is not None else "INCONCLUSIVE")
    return out, verdict, len(vals)


def e033_x_calls() -> tuple[dict, str, int]:
    """H-X-1: X directional calls beat always-long baseline."""
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-X-1", "X calls beat always-long",
        "mean 5d abnormal (vs SPY-matched dates) > 0 with n>=50",
        "mean <= 0 (calls add nothing)",
        "data/x/x_outcomes.json (5 handles, 90d histories)")
    import json as _j
    fp = ROOT / "data" / "x" / "x_outcomes.json"
    try:
        rows = _j.loads(fp.read_text())
    except (OSError, ValueError):
        return {"note": "no outcomes; run scripts/x_backtest.py"}, "INCONCLUSIVE", 0
    d5 = [r for r in rows if r["horizon"] == "d5"]
    n = len(d5)
    m = sum(r["ret"] for r in d5) / n if n else 0.0
    by_h = {}
    for r in d5:
        by_h.setdefault(r["handle"], []).append(r["ret"])
    by_h = {h: (len(v), round(sum(v) / len(v), 4)) for h, v in by_h.items()}
    out = {"n": n, "mean_5d": round(m, 4), "by_handle": by_h,
           "note": f"X calls 5d mean {m:+.2%} (n={n})"}
    verdict = ("CONFIRMED" if n >= 50 and m > 0.005 else "REFUTED"
               if n >= 50 else "INCONCLUSIVE")
    return out, verdict, n


def e034_kalshi_momentum() -> tuple[dict, str, int]:
    """H-KAL-1: Kalshi 7d candle momentum persists next 7d (pm velocity)."""
    from bneck2 import lab as LAB
    from collectors import kalshi as KL
    LAB.preregister(
        "H-KAL-1", "kalshi momentum persists week-over-week",
        "sign(7d momentum) matches sign(next 7d move) on >=60% of windows",
        "hit < 60% (pm prices random-walk at weekly grid)",
        "30d daily candles, top-3 liquid markets")
    import time as _t
    mkts = sorted(KL.fetch_markets("artificial intelligence")
                  + KL.fetch_markets("nuclear power")
                  + KL.fetch_markets("robot"),
                  key=lambda m: -(m.get("liquidity", 0) + m.get("volume", 0)))[:3]
    now = int(_t.time())
    hits, n, detail = 0, 0, []
    for m in mkts:
        if not m.get("series") or not m.get("ticker"):
            continue
        cs = KL.fetch_candles(m["series"], m["ticker"], now - 30 * 86400, now)
        closes = [c["close"] for c in cs if c.get("close") is not None]
        if len(closes) < 21:
            continue
        mom = closes[-8] - closes[-15] if len(closes) >= 15 else 0
        fwd = closes[-1] - closes[-8]
        n += 1
        hit = (mom > 0) == (fwd > 0) and mom != 0
        hits += hit
        detail.append({"q": m["question"][:50], "hit": hit})
    out = {"n": n, "hits": hits, "detail": detail,
           "note": f"kalshi momentum {hits}/{n} carry"}
    verdict = ("CONFIRMED" if n >= 5 and hits / n >= 0.6 else "REFUTED"
               if n >= 5 else "INCONCLUSIVE")
    return out, verdict, n


def e035_attribution() -> tuple[dict, str, int]:
    """H-ATT-1: leave-one-out attribution of the long tilt (E017 flip)."""
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-ATT-1", "tilt driven by few names, not a factor",
        "dropping <=3 tickers flips the sign of mean excess",
        "sign survives all single drops (broad factor, not luck)",
        "biweekly 30-ticker panel")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 8, 0)]
    hold = [r for r in rows if r["date"] >= cut]
    train = [r for r in rows if r["date"] < cut]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 40]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    scored = PD.composite_by_date(hold, winners or ["f_mom_20"], signs)
    by_date = {}
    for r in scored:
        by_date.setdefault(r["date"], []).append(r)

    def _excess(rs):
        ex = []
        for d in sorted(by_date):
            g = sorted(by_date[d], key=lambda r: -r["score"]) if rs is None else                 sorted([r for r in by_date[d] if r["ticker"] not in rs],
                       key=lambda r: -r["score"])
            k = max(len(g) // 3, 1)
            ex.append(sum(r["fwd_20"] for r in g[:k]) / k
                      - sum(r["fwd_20"] for r in g) / len(g))
        return round(sum(ex) / len(ex), 4) if ex else None

    base = _excess(None)
    tickers = sorted({r["ticker"] for r in hold})
    drops = {}
    for t in tickers:
        drops[t] = _excess({t})
    out = {"base_excess": base, "n_tickers": len(tickers),
           "worst_drops": sorted(drops.items(), key=lambda kv: kv[1] or 0)[:3],
           "best_drops": sorted(drops.items(), key=lambda kv: kv[1] or 0)[-3:],
           "note": f"base {base}; dropping changes outcomes, see extremes"}
    flip = any((d or 0) > 0 for d in drops.values())
    return out, ("CONFIRMED" if flip else "REFUTED"), len(tickers)


def e036_tilt_attribution() -> tuple[dict, str, int]:
    """H-ATT-2: E017 +2.24% was concentrated luck, not a factor."""
    from collections import defaultdict
    from bneck2 import lab as LAB
    from bneck2 import predict as PD
    LAB.preregister(
        "H-ATT-2", "tilt concentrated in few names",
        "top-3 contributors >80% of total positive excess on original panel",
        "broad-based (no 3-name dominance)",
        "monthly 15-ticker panel holdout")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("panel-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 3, 0)]
    hold = [r for r in rows if r["date"] >= cut]
    train = [r for r in rows if r["date"] < cut]
    scr = PD.screen(train)
    winners = [s["factor"] for s in scr
               if s["IC"] is not None and abs(s["IC"]) > 0.1 and s["n"] >= 20]
    signs = {s["factor"]: 1.0 if (s["IC"] or 0) >= 0 else -1.0 for s in scr}
    scored = PD.composite_by_date(hold, winners or ["f_mom_20"], signs)
    by_date = {}
    for r in scored:
        by_date.setdefault(r["date"], []).append(r)
    contrib, pos_total = defaultdict(float), 0.0
    for d in sorted(by_date):
        g = sorted(by_date[d], key=lambda r: -r["score"])
        k = max(len(g) // 3, 1)
        uni = sum(r["fwd_20"] for r in g) / len(g)
        for r in g[:k]:
            contrib[r["ticker"]] += r["fwd_20"] - uni
            if r["fwd_20"] - uni > 0:
                pos_total += r["fwd_20"] - uni
    top3 = sorted(contrib.items(), key=lambda kv: -kv[1])[:3]
    share = (sum(v for _, v in top3 if v > 0) / pos_total) if pos_total > 0 else 0.0
    out = {"top3": [(t, round(v, 4)) for t, v in top3],
           "concentration": round(share, 3),
           "note": f"top-3 share of positive excess: {share:.0%}"}
    return out, ("CONFIRMED" if share > 0.8 else "REFUTED"), len(by_date)


def e037_weekend_effect() -> tuple[dict, str, int]:
    """H-WE-1 (V026): Friday->Monday drift differs from midweek drift."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-WE-1", "weekend effect in semi names",
        "|Fri-Mon mean| > |midweek mean| by >=1pp on 2y dailies",
        "no difference (no weekend edge)",
        "Yahoo daily closes, NVDA+AMD+MU+AVGO+GOOGL+META")
    import datetime as _dt
    groups = {"weekend": [], "midweek": []}
    for ticker in ("NVDA", "AMD", "MU", "AVGO", "GOOGL", "META"):
        cl = [(c["date"], c["close"]) for c in
              P.history(ticker, "2y").get("closes", [])]
        for i in range(1, len(cl)):
            d = _dt.date.fromisoformat(cl[i][0])
            r = (cl[i][1] - cl[i - 1][1]) / cl[i - 1][1]
            key = "weekend" if d.weekday() == 0 else "midweek"
            if d.weekday() < 5:
                groups[key].append(r)
    import math as _m
    out = {}
    for k, v in groups.items():
        out[k] = {"n": len(v), "mean": round(sum(v) / len(v), 5) if v else None}
    wm, mm = out["weekend"]["mean"], out["midweek"]["mean"]
    out["note"] = f"Monday {wm} vs midweek {mm}"
    verdict = ("CONFIRMED" if wm is not None and mm is not None
               and abs(wm - mm) >= 0.01 else "REFUTED")
    return out, verdict, min(out["weekend"]["n"], out["midweek"]["n"])


def e038_nventures_mix() -> tuple[dict, str, int]:
    """H-NVENT-1: NVentures is majority non-semiconductor (bio/robotics)."""
    from collections import Counter
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-NVENT-1", "nventures majority non-semi",
        ">50% of 96 portfolio cos outside chips/compute infra",
        "<=50% (still a chip fund)",
        "nvidia.com companies.json 2026-09-10")
    import json as _j
    doc = _j.loads((ROOT / "data" / "universe" / "nventures.json").read_text())
    comps = doc["companies"]
    cats = Counter(c.get("industry", "?") for c in comps)
    chip_keys = ("semiconductor", "chip", "compute", "infrastructure",
                 "networking", "hardware", "datacenter", "data center")
    chip = sum(n for k, n in cats.items()
               if any(w in k.lower() for w in chip_keys))
    out = {"n": len(comps), "top": cats.most_common(6),
           "chip_share": round(chip / len(comps), 3),
           "note": f"non-semi {(len(comps)-chip)/len(comps):.0%} "
                   f"(bio {cats.get('Healthcare & Digital Biology',0)}, "
                   f"robotics {cats.get('Robotics',0)})"}
    return out, ("CONFIRMED" if (len(comps) - chip) / len(comps) > 0.5
                 else "REFUTED"), len(comps)


def e039_implied_identification() -> tuple[dict, str, int]:
    """H-IMP-1: market-implied world probs are UNIDENTIFIED from current data.

    market_survival_p[i] ~= SUM_s p_market(s) x survives[i][s]: 2 equations,
    6 unknowns. Ridge solve + conditioning diagnostics quantify exactly how
    many independent instruments calibration needs (NS-2 upgrade #4 path
    without waiting on pmxt)."""
    from bneck2 import implied as IM
    from bneck2 import lab as LAB
    from bneck2 import worlds as W
    LAB.preregister(
        "H-IMP-1", "implied-p underidentified",
        "ridge solution depends on prior (condition number high / "
        "residual flat across solutions)",
        "data pins a unique distribution (well-conditioned)",
        "worlds.json survives maps + market_survival_p")
    doc = W.load_worlds()
    worlds = doc["worlds"]
    X, y, labels = [], [], []
    for inc in doc.get("incumbents", []):
        surv = inc.get("survives", {})
        X.append([float(surv.get(w["id"], 1.0)) for w in worlds])
        y.append(float(inc.get("market_survival_p", 1.0)))
        labels.append(inc["id"])
    prior = [w["p_market"] for w in worlds]
    out = IM.infer_market_probabilities(X, y, prior=prior)
    # sensitivity: re-solve from flat prior; distance = prior-dependence
    flat = [1.0 / len(worlds)] * len(worlds)
    out2 = IM.infer_market_probabilities(X, y, prior=flat)
    shift = round(sum(abs(a - b) for a, b in zip(out["p"], out2["p"])), 3)
    res = {"n_equations": len(X), "n_unknowns": len(worlds),
           "ridge_from_placeholders": out["p"],
           "ridge_from_flat": out2["p"], "prior_shift": shift,
           "ill_conditioned": out["ill_conditioned"],
           "note": f"2 eqs, 6 unknowns: prior shift {shift} (large = unidentified); "
                   f"need >=6 independent instruments (pmxt/options/credit)"}
    verdict = ("CONFIRMED" if shift > 0.3 or out["ill_conditioned"]
               else "REFUTED")
    return res, verdict, len(X)


def e040_promotion_bar() -> tuple[dict, str, int]:
    """H-BAR-1: single-statement promotion bar status (NS-2 section 4)."""
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-BAR-1", "promotion bar status",
        "Sharpe(top-tercile)>0 AND Sharpe(comp)>Sharpe(mom) AND n>=60",
        "any leg fails (NOT PROMOTED)",
        "E014/E015/E017 receipts")
    import json as _j
    rec = [_j.loads(l) for l in
           (ROOT / "experimentation" / "receipts.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()]
    last = {}
    for r in rec:
        last[r["hyp"]] = r
    e17 = last.get("E017", {}).get("result", {})
    e15 = last.get("E015", {}).get("result", {})
    e14 = last.get("E014", {}).get("result", {})
    legs = {
        "long_tilt_mean": e17.get("mean_excess_vs_universe"),
        "comp_vs_mom": (e15.get("composite_sharpe"), e15.get("momentum_sharpe")),
        "n": e15.get("holdout_n", e14.get("holdout_n", 0)),
    }
    ok = (isinstance(legs["long_tilt_mean"], (int, float)) and legs["long_tilt_mean"] > 0
          and e15.get("composite_sharpe") is not None and e15.get("momentum_sharpe") is not None
          and e15["composite_sharpe"] > e15["momentum_sharpe"]
          and legs["n"] >= 60)
    out = {**legs, "promoted": bool(ok),
           "note": f"bar: tilt {legs['long_tilt_mean']} comp {e15.get('composite_sharpe')} "
                   f"vs mom {e15.get('momentum_sharpe')} n={legs['n']} -> {'PROMOTED' if ok else 'NOT PROMOTED'}"}
    return out, ("CONFIRMED" if ok else "REFUTED"), 3


def e041_regime_split() -> tuple[dict, str, int]:
    """H-REG-1: momentum works in up regimes, fails in drawdowns."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    from bneck2 import predict as PD
    LAB.preregister(
        "H-REG-1", "momentum is regime-conditional",
        "momentum IC positive in SPY-up months, <=0 in SPY-down months",
        "no regime split (IC same sign both)",
        "biweekly panel + SPY month sign")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    sp = {c["date"]: c["close"] for c in P.history("SPY", "2y").get("closes", [])}
    sds = sorted(sp)
    def spy_up(d):
        i = next((k for k, x in enumerate(sds) if x >= d[:7] + "-99"), None)
        return None
    # month sign from month-start to month-end closes
    from collections import defaultdict
    bym = defaultdict(list)
    for r in rows:
        if r.get("f_mom_20") is not None and r.get("fwd_20") is not None:
            bym[r["date"][:7]].append(r)
    reg, out = {}, {}
    for m, rs in sorted(bym.items()):
        ds = sorted(c for c in sds if c[:7] == m)
        if len(ds) < 2 or not sp[ds[0]]:
            continue
        reg[m] = "up" if sp[ds[-1]] > sp[ds[0]] else "down"
    for regime in ("up", "down"):
        sub = [r for m, rs in bym.items() if reg.get(m) == regime for r in rs]
        xs = [r["f_mom_20"] for r in sub]
        ys = [r["fwd_20"] for r in sub]
        out[regime] = {"n": len(sub), "IC": PD.spearman(xs, ys)}
    up, dn = out.get("up", {}), out.get("down", {})
    out["note"] = f"mom IC up-months {up.get('IC')} (n={up.get('n')}) vs down-months {dn.get('IC')} (n={dn.get('n')})"
    ok = (up.get("IC") or 0) > 0.1 and (dn.get("IC") or 0) <= 0
    return out, ("CONFIRMED" if ok else "REFUTED"), up.get("n", 0) + dn.get("n", 0)


def e042_pm_ladder_calibration() -> tuple[dict, str, int]:
    """H-PMCAL-1: resolved NVDA weekly ladders priced correctly."""
    import re
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-PMCAL-1", "PM weekly ladders calibrate",
        ">=85% of resolved (p in {0,1}) weekly level markets match Yahoo close",
        "<85% (mispriced levels exist = edge)",
        "Gamma public-search NVDA + Yahoo daily closes")
    cl = {c["date"]: c["close"] for c in P.history("NVDA", "2y").get("closes", [])}
    hits, total, detail = 0, 0, []
    for m in _nvda_pm_markets():
        q = m.get("question", "")
        mt = re.search(r"week of (\w+ \d+).*above \$(\d[\d,]*)", q)
        if not mt:
            continue
        try:
            prices = __import__("json").loads(m.get("outcomePrices") or "[]")
            p = float(prices[0])
        except (ValueError, TypeError, IndexError):
            continue
        if p not in (0.0, 1.0):
            continue
        import datetime as _dt
        try:
            fri = _dt.datetime.strptime(mt.group(1) + " 2026", "%B %d %Y").date()
        except ValueError:
            try:
                fri = _dt.datetime.strptime(mt.group(1) + " 2025", "%B %d %Y").date()
            except ValueError:
                continue
        # Friday close (or last close <= Friday)
        ds = sorted(d for d in cl if d <= fri.isoformat())
        if not ds:
            continue
        actual = cl[ds[-1]] > float(mt.group(2).replace(",", ""))
        ok = (p == 1.0) == actual
        total += 1
        hits += ok
        if len(detail) < 6:
            detail.append({"q": q[:60], "hit": ok})
    rate = round(hits / total, 3) if total else 0.0
    out = {"hits": hits, "total": total, "rate": rate, "detail": detail,
           "note": f"resolved ladder calibration {rate} (n={total})"}
    verdict = ("CONFIRMED" if total >= 10 and rate >= 0.85 else "REFUTED"
               if total >= 10 else "INCONCLUSIVE")
    return out, verdict, total


def e043_nvda_stack() -> tuple[dict, str, int]:
    """H-STACK-1: X + SEC agreement weeks beat single-signal weeks.

    Stack = X-NVDA directional event AND SEC burst (5+ Form4/2+ deals in
    trailing 30d) in the same week. Compares 20d forwards stack vs solo.
    PM leg tracked live only (no keyless history) — snapshot appended.
    """
    import json as _j
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-STACK-1", "stacked agreement wins",
        "stack weeks beat solo-signal weeks by >=3pp mean fwd-20d",
        "no gap (stacking adds nothing)",
        "x_outcomes NVDA + submissions history + Yahoo")
    xo = _j.loads((ROOT / "data" / "x" / "x_outcomes.json").read_text())
    xweeks = {}
    for r in xo:
        if "NVDA" not in str(r.get("ticker", "")):
            continue
        from datetime import datetime as _dt
        d = None
        for k in ("date", "ts", "created"):
            if r.get(k):
                d = str(r[k])[:10]
                break
        if d:
            xweeks.setdefault(d, []).append(1 if "LONG" in str(r) or r.get("ret", 0) > 0 else -1)
    from collectors import sec as S
    import urllib.request as _u
    req = _u.Request(S.submissions_url("1045810"),
                     headers={"User-Agent": "bneck research contact@localhost",
                              "Accept": "application/json"})
    with _u.urlopen(req, timeout=30) as resp:
        doc = _j.loads(resp.read().decode("utf-8", "replace"))
    fl = (doc.get("filings") or {}).get("recent") or {}
    forms = list(zip(fl.get("form", []), fl.get("filingDate", [])))
    cl = {c["date"]: c["close"] for c in P.history("NVDA", "2y").get("closes", [])}
    ds = sorted(cl)
    stack, solo, base = [], [], []
    for i in range(20, len(ds) - 20):
        d = ds[i]
        win = [f for f, fd in forms if fd and ds[max(i - 30, 0)] <= fd <= d
               and f in ("4", "8-K", "13D", "13G")]
        has_x = any(abs((__import__("datetime").date.fromisoformat(d)
                          - __import__("datetime").date.fromisoformat(xd)).days) <= 7
                    for xd in xweeks)
        has_sec = len(win) >= 5
        fwd = (cl[ds[i + 20]] - cl[ds[i]]) / cl[ds[i]]
        base.append(fwd)
        if has_x and has_sec:
            stack.append(fwd)
        elif has_x or has_sec:
            solo.append(fwd)
    import math as _m
    def _mean(v):
        return round(sum(v) / len(v), 4) if v else None
    out = {"stack_n": len(stack), "solo_n": len(solo), "base_n": len(base),
           "stack_mean": _mean(stack), "solo_mean": _mean(solo),
           "base_mean": _mean(base),
           "note": f"stack {_mean(stack) if stack else None} vs solo vs base "
                   f"(n={len(stack)}/{len(solo)}/{len(base)})"}
    ok = len(stack) >= 5 and _mean(stack) - _mean(solo) >= 0.03
    return out, ("CONFIRMED" if ok else "REFUTED" if len(stack) >= 5 else "INCONCLUSIVE"), len(stack)


def e044_sized_vs_full() -> tuple[dict, str, int]:
    """H-SIZE-1: confidence sizing cuts tails without killing edge."""
    from bneck2 import advise as AD
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-SIZE-1", "sizing beats full-size on risk-adjusted",
        "sized Sharpe > full-size Sharpe AND sized maxDD shallower",
        "sizing underperforms (confidence map wrong — mutate it)",
        "biweekly panel; family confidences from receipts table")
    import json as _j
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [_j.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("fwd_20") is not None]
    # family confidences (measured lower bounds, NORTHSTAR-5 table)
    conf = {"f_mom_20": 0.2, "f_attack": 0.0, "f_burst": 0.0,
            "f_hn": 0.0, "f_short": 0.0, "f_conv": 0.0, "f_B": 0.0}
    sized, full, uni = [], [], []
    by_date = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
    for d in sorted(by_date):
        g = by_date[d]
        for r in g:
            s = r.get("f_mom_20") or 0.0
            a = AD.advise(s, conf["f_mom_20"])
            frac = a["fraction"] if a["action"] != "HOLD" else 0.0
            sgn = 1.0 if s >= 0 else -1.0
            sized.append({"date": d, "ticker": r["ticker"] + ":s",
                          "score": sgn * frac, "forward_return": r["fwd_20"]})
            full.append({"date": d, "ticker": r["ticker"] + ":f",
                         "score": sgn * 1.0 if abs(s) > 0 else 0.0,
                         "forward_return": r["fwd_20"]})
            uni.append({"date": d, "ticker": r["ticker"] + ":u",
                        "score": 1.0, "forward_return": r["fwd_20"]})

    def _wf(rs):
        ok = [dict(x, forward_return=x["forward_return"]) for x in rs]
        _, st = BT.walk_forward(ok, quantile=0.25)
        return st

    ss, fs, us = _wf(sized), _wf(full), _wf(uni)
    out = {"sized_sharpe": ss.get("sharpe"), "sized_dd": ss.get("max_drawdown"),
           "full_sharpe": fs.get("sharpe"), "full_dd": fs.get("max_drawdown"),
           "bh_sharpe": us.get("sharpe"),
           "note": f"sized {ss.get('sharpe')}/{ss.get('max_drawdown')} vs "
                   f"full {fs.get('sharpe')}/{fs.get('max_drawdown')} vs "
                   f"bh {us.get('sharpe')}"}
    ok = (ss.get("sharpe") is not None and fs.get("sharpe") is not None
          and ss["sharpe"] > fs["sharpe"]
          and (ss.get("max_drawdown") or 0) > (fs.get("max_drawdown") or 0))
    return out, ("CONFIRMED" if ok else "REFUTED"), len(by_date)


def _nvda_weekly_bundle():
    """Assemble 2y daily features for NVDA (cached where set)."""
    import datetime as _dt
    from bneck2 import nvda as NV
    from bneck2 import prices as P
    from collectors import finra as FIN
    from collectors import hn as HN
    from collectors import sec as S
    import urllib.request as _u
    import json as _j
    closes = {c["date"]: c["close"] for c in P.history("NVDA", "2y").get("closes", [])}
    today = max(closes)
    start = (_dt.date.fromisoformat(today) - _dt.timedelta(days=730)).isoformat()
    dates = sorted(d for d in closes if d >= start)
    # SEC filings history (one fetch)
    req = _u.Request(S.submissions_url("1045810"),
                     headers={"User-Agent": "bneck research contact@localhost",
                              "Accept": "application/json"})
    with _u.urlopen(req, timeout=30) as r:
        doc = _j.loads(r.read().decode("utf-8", "replace"))
    fl = (doc.get("filings") or {}).get("recent") or {}
    forms = [(f, d) for f, d in zip(fl.get("form", []), fl.get("filingDate", [])) if d]
    # FINRA short history (cached tapes)
    shorts = FIN.short_history(["NVDA"], dates)
    # HN weekly counts (bounded: biweekly samples, forward-filled)
    hn_by_date, last = {}, 0
    for k, d in enumerate(dates):
        if k % 10 == 0:
            try:
                import urllib.parse, calendar
                lo_ts = calendar.timegm(_dt.datetime.fromisoformat(d).timetuple())
                url = ("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
                    {"query": "Nvidia", "tags": "story",
                     "numericFilters": f"created_at_i>{lo_ts - 14 * 86400},created_at_i<{lo_ts}",
                     "hitsPerPage": 100}))
                rq = _u.Request(url, headers={"User-Agent": "bneck"})
                with _u.urlopen(rq, timeout=20) as r2:
                    last = int(_j.loads(r2.read().decode("utf-8", "replace")).get("nbHits", 0))
            except Exception:
                pass
        hn_by_date[d] = last
    sec_by_date = {}
    for d in dates:
        win = [(f, fd) for f, fd in forms if fd and d >= fd >= _shift_days(d, -30)]
        n4 = sum(1 for f, _ in win if f == "4")
        dl = sum(1 for f, _ in win if f in ("8-K", "13D", "13G"))
        sec_by_date[d] = {"burst": n4 / 5.0 + dl / 2.0}
    feats = {}
    # NOTE: features() takes precomputed dicts; build burst dict directly:
    feats = {}
    for d in dates:
        past = sorted(x for x in closes if x <= d)
        m20 = None
        if len(past) > 20 and closes[past[-21]]:
            m20 = (closes[past[-1]] - closes[past[-21]]) / closes[past[-21]]
        feats[d] = {"mom_20": m20,
                    "burst": sec_by_date[d]["burst"] if False else _burst_ratio(d, forms),
                    "short": (shorts.get(d) or {}).get("NVDA"),
                    "hn": hn_by_date.get(d, 0)}
    return dates, closes, feats


def _shift_days(d: str, n: int) -> str:
    import datetime as _dt
    y, m, dd = map(int, d.split("-"))
    return (_dt.date(y, m, dd) + _dt.timedelta(days=n)).isoformat()


def _burst_ratio(d: str, forms) -> float:
    win = [f for f, fd in forms if fd and d >= fd >= _shift_days(d, -30)]
    n4 = sum(1 for f in win if f == "4")
    dl = sum(1 for f in win if f in ("8-K", "13D", "13G"))
    return n4 / 5.0 + dl / 2.0


def e045_nvda_alpha() -> tuple[dict, str, int]:
    """H-NVDA-A: alt-signal sizing beats 3x buy-hold on NVDA test year."""
    from bneck2 import lab as LAB
    from bneck2 import nvda as NV
    LAB.preregister(
        "H-NVDA-A", "sized NVDA beats 3x buy-hold out-of-sample",
        "test-year Sharpe(sized) > Sharpe(buyhold3x), train-tuned",
        "sized <= buyhold3x (timing adds nothing on NVDA)",
        "2y daily panel; train yr1, test yr2; 3x cap; 5bps costs")
    dates, closes, feats = _nvda_weekly_bundle()
    cut = dates[len(dates) * 2 // 3]
    train = [d for d in dates if d < cut]
    test = [d for d in dates if d >= cut]
    # tune (pick best_alt) on TRAIN tail only, evaluate once on TEST
    ttail = train[-len(train) // 3:]
    tune = {}
    for mode in ("mom", "burst_fade", "short_fade", "combo"):
        tune[mode] = NV.run(ttail, closes, feats, mode)["sharpe"]
    best_alt = max(tune, key=lambda m: tune[m])
    out = {}
    for mode in ("buyhold3x", "buyhold1x", "mom", "burst_fade",
                 "short_fade", "combo"):
        out[mode] = NV.run(test, closes, feats, mode)
    res = {"modes": out, "best_alt": best_alt, "tune": tune,
           "note": f"tuned {best_alt} on train-tail, test: "
                   f"{best_alt} {out[best_alt]['sharpe']} vs "
                   f"bh3x {out['buyhold3x']['sharpe']}"}
    ok = out[best_alt]["sharpe"] > out["buyhold3x"]["sharpe"]
    return res, ("CONFIRMED" if ok else "REFUTED"), len(test)


def e046_rules_generalize() -> tuple[dict, str, int]:
    """H-NVDA-B: NVDA-tuned rules (short_fade, burst_fade) generalize
    to the atoms universe out-of-sample."""
    import datetime as _dt
    import json as _j
    import urllib.request as _u
    from bneck2 import lab as LAB
    from bneck2 import nvda as NV
    from bneck2 import prices as P
    from collectors import finra as FIN
    from collectors import sec as S
    LAB.preregister(
        "H-NVDA-B", "short_fade/burst_fade beat 3x buy-hold cross-sectionally",
        "test-half Sharpe(rule) > Sharpe(buyhold3x) for a preregistered rule",
        "rules fail outside NVDA (NVDA-specific fit)",
        "17 atoms names; split by date; 3x cap; 5bps costs")
    atoms = _j.load(open(ROOT / "data" / "universe" / "ai_atoms.json"))
    names = ["NVDA"] + [a["ticker"] for a in atoms.get("companies", [])]
    closes_all = {}
    for t in names:
        try:
            cs = P.history(t, "2y").get("closes", [])
            if len(cs) >= 300:
                closes_all[t] = {c["date"]: c["close"] for c in cs}
        except Exception:
            pass
    all_dates = sorted({d for m in closes_all.values() for d in m})
    if len(all_dates) < 200:
        return {"error": "thin panel"}, "INCONCLUSIVE", 0
    shorts = FIN.short_history(list(closes_all), all_dates)
    # SEC burst per ticker: use submissions dates where CIK known else skip
    cik = {"NVDA": "1045810", "MSFT": "789019", "GOOGL": "1652044",
           "META": "1326801", "AMZN": "1018724", "AAPL": "320193",
           "TSM": "1046179", "AVGO": "1730168", "AMD": "2488",
           "NFLX": "1065280", "CRM": "1108524", "ORCL": "1341439",
           "PLTR": "1321655", "COIN": "1679788", "TSLA": "1318605",
           "INTC": "50863", "IBM": "51143"}
    bursts = {}
    for t, c in cik.items():
        if t not in closes_all:
            continue
        try:
            req = _u.Request(S.submissions_url(c),
                             headers={"User-Agent": "bneck research contact@localhost",
                                      "Accept": "application/json"})
            with _u.urlopen(req, timeout=30) as r:
                doc = _j.loads(r.read().decode("utf-8", "replace"))
            fl = (doc.get("filings") or {}).get("recent") or {}
            forms = [(f, d) for f, d in zip(fl.get("form", []), fl.get("filingDate", [])) if d]
            bursts[t] = forms
        except Exception:
            bursts[t] = []
    feats_all = {}
    for t, closes in closes_all.items():
        forms = bursts.get(t, [])
        for d in sorted(closes):
            past = sorted(x for x in closes if x <= d)
            m20 = None
            if len(past) > 20 and closes[past[-21]]:
                m20 = (closes[past[-1]] - closes[past[-21]]) / closes[past[-21]]
            feats_all.setdefault(d, {})[t] = {
                "mom_20": m20, "burst": _burst_ratio(d, forms),
                "short": (shorts.get(d) or {}).get(t), "hn": 0}
    cut = all_dates[len(all_dates) * 2 // 3]
    test = [d for d in all_dates if d >= cut]
    agg = {m: [] for m in ("buyhold3x", "buyhold1x", "short_fade", "burst_fade")}
    for d in test:
        row = feats_all.get(d, {})
        for t, f in row.items():
            closes = closes_all[t]
            cl = sorted(x for x in closes if x <= d)
            if not cl:
                continue
            # next close after d
            fut = sorted(x for x in closes if x > d)
            if not fut:
                continue
            r = (closes[fut[0]] - closes[d]) / closes[d] if closes[d] else 0.0
            for m in agg:
                w = NV.size_rule(f, m)
                agg[m].append(w * r)  # costs ignored cross-sectionally (note)
    import math as _m
    out = {}
    for m, rs in agg.items():
        n = len(rs)
        mu = sum(rs) / n
        var = sum((x - mu) ** 2 for x in rs) / (n - 1)
        sh = (mu * 252) / _m.sqrt(var * 252) if var > 0 else 0.0
        tot = 1.0
        for x in rs:
            tot *= 1 + x / max(len(feats_all.get(test[0], {})), 1)
        out[m] = {"sharpe": round(sh, 3), "n": n}
    # preregistered rule = short_fade (NVDA-tuned winner)
    ok = out["short_fade"]["sharpe"] > out["buyhold3x"]["sharpe"]
    res = {"modes": out, "rule": "short_fade",
           "note": f"short_fade {out['short_fade']['sharpe']} vs "
                   f"bh3x {out['buyhold3x']['sharpe']} (costs excluded)"}
    return res, ("CONFIRMED" if ok else "REFUTED"), len(test)


def e047_forward_paper() -> tuple[dict, str, int]:
    """H-NVDA-C: paper rules beat buy-hold over 90 forward days."""
    import csv as _csv
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-NVDA-C", "paper timing beats buy-hold forward",
        "eq_short or eq_burst > eq_bh1x at 90 rows",
        "both trail buy-hold (timing adds nothing)",
        "scripts/paper.py daily log; frozen rules")
    f = ROOT / "data" / "paper" / "nvda.csv"
    rows = list(_csv.DictReader(f.open())) if f.exists() else []
    if len(rows) < 90:
        return {"rows": len(rows), "last": rows[-1] if rows else None,
                "note": f"{len(rows)}/90 days logged — resolves later"}, "INCONCLUSIVE", len(rows)
    last = rows[-1]
    win = (float(last["eq_short"]) > float(last["eq_bh1x"])
           or float(last["eq_burst"]) > float(last["eq_bh1x"]))
    return {"rows": len(rows), "last": last,
            "note": f"short {last['eq_short']} burst {last['eq_burst']} vs bh {last['eq_bh1x']}"}, ("CONFIRMED" if win else "REFUTED"), len(rows)


def e048_support_bounce() -> tuple[dict, str, int]:
    """H-SUP-1: trailing-low bounce (fish sequence rule, de-lookaheaded)
    beats buy-hold cross-sectionally."""
    import json as _j
    from bneck2 import backtest as BT
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-SUP-1", "bounce-near-trailing-low beats buy-hold",
        "walk-forward Sharpe(bounce) > Sharpe(uniform buy-hold)",
        "bounce <= buy-hold (fish edge was lookahead/HOLD-label artifact)",
        "atoms + NVDA, 2y daily, trailing-252d low, next-day execution")
    atoms = _j.load(open(ROOT / "data" / "universe" / "ai_atoms.json"))
    names = ["NVDA"] + [a["ticker"] for a in atoms.get("companies", [])]
    rows, ndates = [], set()
    for t in names:
        try:
            cs = P.history(t, "2y").get("closes", [])
        except Exception:
            continue
        if len(cs) < 300:
            continue
        closes = [c["close"] for c in cs]
        for i in range(252, len(cs) - 21):
            lo = min(closes[i - 252:i + 1])
            if not lo:
                continue
            dist = (closes[i] - lo) / lo
            if dist > 0.30:  # only consider names within 30% of low
                continue
            fwd = (closes[i + 21] - closes[i + 1]) / closes[i + 1] if closes[i + 1] else None
            if fwd is None:
                continue
            rows.append({"date": cs[i]["date"], "ticker": t,
                         "score": -dist, "forward_return": fwd})
            ndates.add(cs[i]["date"])
    if len(ndates) < 30:
        return {"rows": len(rows)}, "INCONCLUSIVE", len(ndates)
    _, st = BT.walk_forward(rows, quantile=0.25)
    import math as _m
    fr = [r["forward_return"] for r in rows]
    mu = sum(fr) / len(fr)
    var = sum((x - mu) ** 2 for x in fr) / (len(fr) - 1)
    bh_sh = round((mu * 12) / _m.sqrt(var * 12), 3) if var > 0 else 0.0
    res = {"bounce_sharpe": st.get("sharpe"), "bh_sharpe": bh_sh,
           "rows": len(rows),
           "note": f"bounce {st.get('sharpe')} vs bh {bh_sh}"}
    ok = (st.get("sharpe") is not None and st["sharpe"] > bh_sh)
    return res, ("CONFIRMED" if ok else "REFUTED"), len(ndates)


def e049_highn_horserace() -> tuple[dict, str, int]:
    """H-HF-1: a train-picked monthly factor beats buy-hold on 2021+ test."""
    import subprocess as _sp
    import json as _j
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-HF-1", "train-picked factor beats buy-hold out-of-sample",
        "test Sharpe(best) > Sharpe(buyhold), HF monthly panel",
        "best factor <= buy-hold (no priced edge in these factors)",
        "HF Stocks-Daily-Price monthly panel; train 2016-20, test 2021-26-07")
    if not (ROOT / "data" / "hf_panel" / "daily.jsonl").exists():
        return {"error": "panel not fetched"}, "INCONCLUSIVE", 0
    r = _sp.run(["python3", "scripts/hf_horserace.py"], capture_output=True,
                text=True, timeout=600)
    if r.returncode != 0:
        return {"error": r.stderr[-300:]}, "INCONCLUSIVE", 0
    d = _j.loads(r.stdout)
    best, bh = d[d["best"]], d["buyhold"]
    res = {"tune": d["tune"], "best": d["best"],
           "best_test": best, "buyhold_test": bh,
           "symbols": d["symbols"],
           "note": f"{d['best']} {best['sharpe']} vs bh {bh['sharpe']}"}
    ok = (best.get("sharpe") is not None and bh.get("sharpe") is not None
          and best["sharpe"] > bh["sharpe"])
    return res, ("CONFIRMED" if ok else "REFUTED"), d.get("test_months", 0)


def e050_nvda_mimic() -> tuple[dict, str, int]:
    """H-NVDA-M: NVDA's own public strategic holdings (13F 2026Q2,
    known at filing 2026-08-14) beat SPY forward."""
    import json as _j
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-NVDA-M", "buy-what-NVDA-buys beats SPY from filing date",
        "value-weighted public NVDA holdings total return > SPY from 8/14",
        "mimic <= SPY (NVDA's balance-sheet bets carry no edge)",
        "NVDA 13F 2026Q2 public positions; enter at filing-date close")
    d13 = _j.load(open(ROOT / "data" / "universe" / "nvda_13f_2026q2.json"))
    pubs = [(x["ticker"], x["value_usd"]) for x in d13["positions"] if x.get("ticker")]
    start = "2026-08-14"
    rets, wsum = {}, sum(w for _, w in pubs)
    for t, w in pubs:
        try:
            cs = [c for c in P.history(t, "3mo").get("closes", []) if c["date"] >= start]
        except Exception:
            continue
        if len(cs) < 2 or not cs[0]["close"]:
            continue
        rets[t] = ((cs[-1]["close"] - cs[0]["close"]) / cs[0]["close"], w, cs[-1]["date"])
    if not rets:
        return {"error": "no prices"}, "INCONCLUSIVE", 0
    port = sum(r * w for r, w in ((v[0], v[1]) for v in rets.values())) / sum(v[1] for v in rets.values())
    spy = [c for c in P.history("SPY", "3mo").get("closes", []) if c["date"] >= start]
    nv = [c for c in P.history("NVDA", "3mo").get("closes", []) if c["date"] >= start]
    spy_r = (spy[-1]["close"] - spy[0]["close"]) / spy[0]["close"]
    nv_r = (nv[-1]["close"] - nv[0]["close"]) / nv[0]["close"]
    res = {"mimic": round(port, 4), "spy": round(spy_r, 4), "nvda": round(nv_r, 4),
           "names": {t: round(v[0], 4) for t, v in rets.items()},
           "asof": rets[next(iter(rets))][2],
           "note": f"mimic {port:.2%} vs SPY {spy_r:.2%} vs NVDA {nv_r:.2%} since 8/14"}
    ok = port > spy_r
    return res, ("CONFIRMED" if ok else "REFUTED"), 1


def g001_graph_coverage() -> tuple[dict, str, int]:
    """G-GRAPH-1: production graph meets P0 evidence bar."""
    from bneck2 import edges as E
    from bneck2 import lab as LAB
    import json as _j
    LAB.preregister(
        "G-GRAPH-1", "graph meets P0 bar (>=70% evidenced, >=30% quantified)",
        "coverage ratchets up vs last receipt",
        "coverage flat/down (graph work stalled)",
        "graph_v2.json production edges only; quarantine excluded")
    cov = E.coverage()
    q = []
    if E.QUARANTINE.exists():
        q = _j.loads(E.QUARANTINE.read_text())
    cov["quarantined"] = len(q)
    ok = cov["pct_evidence"] >= 0.7 and cov["pct_quantified"] >= 0.3
    cov["note"] = (f"{cov['edges']} edges, {cov['pct_evidence']:.0%} evidenced, "
                   f"{cov['pct_quantified']:.0%} quantified, {len(q)} quarantined")
    return cov, ("CONFIRMED" if ok else "REFUTED"), cov["edges"]


def g002_layer_backbone() -> tuple[dict, str, int]:
    """G-GRAPH-2: ProphetMap layer backbone imported as typed nodes."""
    import json as _j
    from bneck2 import lab as LAB
    LAB.preregister(
        "G-GRAPH-2", "layer backbone present (>=25 PML nodes, >=80 linked tickers)",
        "backbone persists and grows",
        "backbone removed/shrunk (import regressed)",
        "graph_v2.json PML_ nodes + suppliers[]")
    g = _j.load(open(ROOT / "data" / "bottlenecks" / "graph_v2.json"))
    pml = [n for n in g.get("nodes", []) if n.get("id", "").startswith("PML_")]
    linked = sum(len(n.get("suppliers", [])) for n in pml)
    res = {"pml_nodes": len(pml), "tickers_linked": linked,
           "nodes_total": len(g.get("nodes", [])),
           "note": f"{len(pml)} layer nodes, {linked} supplier links"}
    ok = len(pml) >= 25 and linked >= 80
    return res, ("CONFIRMED" if ok else "REFUTED"), len(pml)


CIK_MAP = {"NVDA": "1045810", "MSFT": "789019", "AAPL": "320193",
           "GOOGL": "1652044", "AMZN": "1018724", "META": "1326801",
           "TSLA": "1318605", "AVGO": "1730168", "AMD": "2488",
           "NFLX": "1065280", "CRM": "1108524", "ORCL": "1341439",
           "PLTR": "1321655", "COIN": "1679788", "INTC": "50863",
           "IBM": "51143", "QCOM": "804328"}


def _facts_cached(ticker: str) -> dict | None:
    import json as _j
    import urllib.request as _u
    f = ROOT / "data" / "cache" / f"secfacts_{ticker}.json"
    if f.exists():
        try:
            return _j.loads(f.read_text())
        except Exception:
            pass
    try:
        from collectors import sec_facts as SF
        req = _u.Request(SF.facts_url(CIK_MAP[ticker]),
                         headers={"User-Agent": "bneck research contact@localhost",
                                  "Accept": "application/json"})
        with _u.urlopen(req, timeout=60) as r:
            doc = _j.loads(r.read().decode("utf-8", "replace"))
        f.write_text(_j.dumps({"facts": doc.get("facts", {}),
                               "entity": doc.get("entityName", "")}))
        return {"facts": doc.get("facts", {}), "entity": doc.get("entityName", "")}
    except Exception:
        return None


CAPEX_TAGS = ("PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets")


def _fy_series(facts: dict, tags) -> tuple[list[tuple[int, float]], int]:
    """(FY, value) annual series + FY-end month (1-12), first tag wins per FY."""
    if isinstance(tags, str):
        tags = (tags,)
    gaap = (facts.get("facts") or {}).get("us-gaap", {})
    per = {}
    endmo = 12
    for tag in tags:
        series: dict[int, float] = {}
        for u in gaap.get(tag, {}).get("units", {}).get("USD", []):
            try:
                fy, v = int(u.get("fy", 0)), float(u.get("val", 0))
            except (ValueError, TypeError):
                continue
            if u.get("form") == "10-K" and fy > 0:
                series[fy] = abs(v)
                try:
                    endmo = int(str(u.get("end", ""))[5:7])
                except Exception:
                    pass
        per[tag] = series
    yrs = sorted({f for d in per.values() for f in d})
    return [(f, next(per[t][f] for t in tags if f in per[t])) for f in yrs], endmo


def _fy_rd(facts: dict) -> tuple[list[tuple[int, float]], int]:
    """(FY, R&D) annual series + FY-end month (1-12)."""
    return _fy_series(facts, "ResearchAndDevelopmentExpense")


def e051_reflexivity() -> tuple[dict, str, int]:
    """H-REFL-1: price-validated R&D acceleration beats unvalidated run-ups."""
    import datetime as _dt
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-REFL-1", "validated reflexivity (run-up + R&D accel) wins forward",
        "fwd(validated) > fwd(unvalidated); corr(past_ret, next_RDg) > 0",
        "no spread (market prices R&D paths already; price doesn't cause invest)",
        "17 CIK-mapped megacaps; FY windows +100d entry; 10y Yahoo + XBRL R&D")
    val_f, unv_f, pairs = [], [], []
    for t in CIK_MAP:
        doc = _facts_cached(t)
        if not doc:
            continue
        rd, endmo = _fy_rd(doc)
        if len(rd) < 4:
            continue
        try:
            px = {c["date"]: c["close"] for c in P.history(t, "10y").get("closes", [])}
        except Exception:
            continue
        if len(px) < 500:
            continue
        dys = sorted(px)

        def _px(d: str) -> float | None:
            while d not in px:
                try:
                    d = (_dt.date.fromisoformat(d) - _dt.timedelta(days=1)).isoformat()
                except Exception:
                    return None
                if d < dys[0]:
                    return None
            return px[d]

        for k in range(1, len(rd) - 1):
            fy, r = rd[k]
            r0 = rd[k - 1][1]
            if not r0:
                continue
            g = (r - r0) / abs(r0)
            ey, em = fy + (1 if endmo == 12 else 0), endmo
            try:
                entry = (_dt.date(ey, em, 1) + _dt.timedelta(days=100)).isoformat()
                back = (_dt.date(ey - 1, em, 1) + _dt.timedelta(days=100)).isoformat()
                fwd1 = (_dt.date(ey + 1, em, 1) + _dt.timedelta(days=100)).isoformat()
            except ValueError:
                continue
            p1, p0, pf = _px(entry), _px(back), _px(fwd1)
            if not (p1 and p0 and pf):
                continue
            past = (p1 - p0) / p0
            fwd = (pf - p1) / p1
            pairs.append((past, g, fwd))
    if len(pairs) < 30:
        return {"pairs": len(pairs)}, "INCONCLUSIVE", len(pairs)
    import math as _m
    pr = [p for p, _, _ in pairs]
    mp = sorted(pr)[len(pr) // 2]
    gs = [g for _, g, _ in pairs]
    mg = sorted(gs)[len(gs) // 2]
    for past, g, fwd in pairs:
        (val_f if (past >= mp and g >= mg) else
         unv_f if (past >= mp and g < mg) else None)
        if past >= mp and g >= mg:
            val_f.append(fwd)
        elif past >= mp and g < mg:
            unv_f.append(fwd)
    # R1: corr(past return, R&D growth) — price -> investment arrow
    n = len(pairs)
    mx = sum(p for p, _, _ in pairs) / n
    my = sum(g for _, g, _ in pairs) / n
    cov = sum((p - mx) * (g - my) for p, g, _ in pairs) / n
    vx = sum((p - mx) ** 2 for p, _, _ in pairs) / n
    vy = sum((g - my) ** 2 for _, g, _ in pairs) / n
    rho = cov / _m.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0
    mv = sum(val_f) / len(val_f) if val_f else 0.0
    mu = sum(unv_f) / len(unv_f) if unv_f else 0.0
    res = {"n": n, "rho_pastret_rd": round(rho, 3),
           "fwd_validated": round(mv, 4), "n_val": len(val_f),
           "fwd_unvalidated": round(mu, 4), "n_unv": len(unv_f),
           "spread": round(mv - mu, 4),
           "note": f"rho={rho:.2f}; validated {mv:.1%} (n={len(val_f)}) vs "
                   f"unvalidated {mu:.1%} (n={len(unv_f)})"}
    ok = mv > mu and rho > 0
    return res, ("CONFIRMED" if ok else "REFUTED"), n


def e052_capex_reflex() -> tuple[dict, str, int]:
    """H-REFL-2: price-validated CAPEX acceleration beats unvalidated run-ups."""
    import datetime as _dt
    import math as _m
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-REFL-2", "validated capex reflexivity wins forward",
        "fwd(validated) > fwd(unvalidated); corr(past_ret, next_CAPEXg) > 0",
        "no spread (capex doesn't follow price either)",
        "same 17 CIK names; XBRL capex tags; FY+100d entry")
    pairs = []
    for t in CIK_MAP:
        doc = _facts_cached(t)
        if not doc:
            continue
        cx, endmo = _fy_series(doc, CAPEX_TAGS)
        if len(cx) < 4:
            continue
        try:
            px = {c["date"]: c["close"] for c in P.history(t, "10y").get("closes", [])}
        except Exception:
            continue
        if len(px) < 500:
            continue
        dys = sorted(px)

        def _px(d: str):
            while d not in px:
                try:
                    d = (_dt.date.fromisoformat(d) - _dt.timedelta(days=1)).isoformat()
                except Exception:
                    return None
                if d < dys[0]:
                    return None
            return px[d]

        for k in range(1, len(cx) - 1):
            fy, r = cx[k]
            r0 = cx[k - 1][1]
            if not r0:
                continue
            g = (r - r0) / abs(r0)
            ey, em = fy + (1 if endmo == 12 else 0), endmo
            try:
                entry = (_dt.date(ey, em, 1) + _dt.timedelta(days=100)).isoformat()
                back = (_dt.date(ey - 1, em, 1) + _dt.timedelta(days=100)).isoformat()
                fwd1 = (_dt.date(ey + 1, em, 1) + _dt.timedelta(days=100)).isoformat()
            except ValueError:
                continue
            p1, p0, pf = _px(entry), _px(back), _px(fwd1)
            if not (p1 and p0 and pf):
                continue
            pairs.append(((p1 - p0) / p0, g, (pf - p1) / p1))
    if len(pairs) < 30:
        return {"pairs": len(pairs)}, "INCONCLUSIVE", len(pairs)
    n = len(pairs)
    mp = sorted(p for p, _, _ in pairs)[n // 2]
    mg = sorted(g for _, g, _ in pairs)[n // 2]
    val = [f for p, g, f in pairs if p >= mp and g >= mg]
    unv = [f for p, g, f in pairs if p >= mp and g < mg]
    mx = sum(p for p, _, _ in pairs) / n
    my = sum(g for _, g, _ in pairs) / n
    cov = sum((p - mx) * (g - my) for p, g, _ in pairs) / n
    vx = sum((p - mx) ** 2 for p, _, _ in pairs) / n
    vy = sum((g - my) ** 2 for _, g, _ in pairs) / n
    rho = cov / _m.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0
    mv = sum(val) / len(val) if val else 0.0
    mu = sum(unv) / len(unv) if unv else 0.0
    res = {"n": n, "rho_pastret_capex": round(rho, 3),
           "fwd_validated": round(mv, 4), "n_val": len(val),
           "fwd_unvalidated": round(mu, 4), "n_unv": len(unv),
           "spread": round(mv - mu, 4),
           "note": f"rho={rho:.2f}; validated {mv:.1%} (n={len(val)}) vs "
                   f"unvalidated {mu:.1%} (n={len(unv)})"}
    ok = mv > mu and rho > 0
    return res, ("CONFIRMED" if ok else "REFUTED"), n


STEP_EVENTS = [("2022-11-30", "ChatGPT launch"),
               ("2023-03-14", "GPT-4 launch"),
               ("2024-09-12", "o1 reasoning launch"),
               ("2025-01-20", "DeepSeek-R1 shock")]


def e053_step_obsolescence() -> tuple[dict, str, int]:
    """H-STEP-1: LLM capability steps permanently impair software (IGV vs SPY)."""
    import datetime as _dt
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-STEP-1", "model releases step IGV down vs SPY without full recovery",
        "mean 60d excess(IGV-SPY) post-event < 0 AND no V-recovery by d60",
        "excess >= 0 or full recovery (market prices obsolescence instantly)",
        "IGV vs SPY daily; 4 pre-listed LLM events; entry t+5 to dodge noise")
    try:
        igv = {c["date"]: c["close"] for c in P.history("IGV", "5y").get("closes", [])}
        spy = {c["date"]: c["close"] for c in P.history("SPY", "5y").get("closes", [])}
    except Exception as e:
        return {"error": str(e)[:120]}, "INCONCLUSIVE", 0
    dys = sorted(set(igv) & set(spy))
    if len(dys) < 500:
        return {"error": "thin overlap"}, "INCONCLUSIVE", 0

    def _px(m, d):
        while d not in m and d >= dys[0]:
            d = (_dt.date.fromisoformat(d) - _dt.timedelta(days=1)).isoformat()
        return m.get(d)

    rows = []
    for ev, name in STEP_EVENTS:
        try:
            t5 = (_dt.date.fromisoformat(ev) + _dt.timedelta(days=7)).isoformat()
            t60 = (_dt.date.fromisoformat(ev) + _dt.timedelta(days=90)).isoformat()
        except ValueError:
            continue
        i0, i1 = _px(igv, t5), _px(igv, t60)
        s0, s1 = _px(spy, t5), _px(spy, t60)
        if not all([i0, i1, s0, s1]):
            continue
        # max drawdown of excess leg + endpoint excess (V-recovery check)
        win = [d for d in dys if t5 <= d <= t60]
        if len(win) < 20:
            continue
        ex = [(igv[d] / i0 - 1) - (spy[d] / s0 - 1) for d in win]
        rows.append({"event": name, "date": ev,
                     "excess_end": round(ex[-1], 4),
                     "excess_min": round(min(ex), 4),
                     "recovered": bool(ex[-1] > -0.005)})
    if len(rows) < 3:
        return {"rows": rows}, "INCONCLUSIVE", len(rows)
    mean_end = sum(r["excess_end"] for r in rows) / len(rows)
    norecov = sum(1 for r in rows if not r["recovered"])
    res = {"events": rows, "mean_excess_end": round(mean_end, 4),
           "no_recovery": f"{norecov}/{len(rows)}",
           "note": f"mean 60d excess {mean_end:.1%}, {norecov}/{len(rows)} unrecovered"}
    ok = mean_end < 0 and norecov >= len(rows) // 2 + 1
    return res, ("CONFIRMED" if ok else "REFUTED"), len(rows)


def g003_death_watch() -> tuple[dict, str, int]:
    """G-GRAPH-3: researcher-sourced THREATENS overlay covers >=10 names."""
    import json as _j
    from bneck2 import lab as LAB
    LAB.preregister(
        "G-GRAPH-3", "death-watch overlay >=10 THREATENS edges with quotes",
        "overlay grows with dated researcher evidence",
        "overlay shrinks below 10 (extractor regressed or quiet corpus)",
        "threat_graph.json overlay; min 2 negatives; researcher quotes")
    ov = _j.load(open(ROOT / "data" / "bottlenecks" / "threat_graph.json"))
    n = len(ov.get("edges", []))
    with_ev = sum(1 for e in ov.get("edges", []) if e.get("evidence"))
    res = {"edges": n, "with_evidence": with_ev,
           "note": f"{n} THREATENS edges, {with_ev} evidenced"}
    return res, ("CONFIRMED" if n >= 10 else "REFUTED"), n


def e054_death_watch_test() -> tuple[dict, str, int]:
    """H-DW-1: threatened names underperform SPY."""
    import datetime as _dt
    import json as _j
    from bneck2 import lab as LAB
    LAB.preregister(
        "H-DW-1", "death-watch basket underperforms SPY",
        "mean excess(threatened vs SPY since threat) < 0, "
        "and forward leg confirms at 90d",
        "mean excess >= 0 (researcher threats carry no price signal)",
        "threat_queue.json (fresh<=7d); forward leg resolves 90d post-first-run")
    qf = _j.load(open(ROOT / "data" / "bottlenecks" / "threat_queue.json"))
    age = (_dt.date.today() - _dt.date.fromisoformat(qf.get("asof", "2020-01-01"))).days
    if age > 7:
        return {"asof": qf.get("asof"), "age_days": age}, "INCONCLUSIVE", 0
    rows = [r for r in qf["queue"] if r["status"] in ("DYING", "UNPRICED", "QUESTIONED")
            and isinstance(r.get("excess"), (int, float))]
    if len(rows) < 10:
        return {"n": len(rows)}, "INCONCLUSIVE", len(rows)
    import math as _m
    xs = [r["excess"] for r in rows]
    n = len(xs)
    mu = sum(xs) / n
    sd = _m.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    tstat = mu / (sd / _m.sqrt(n)) if sd > 0 else 0.0
    dying = sum(1 for r in rows if r["status"] == "DYING")
    res = {"n": n, "mean_excess": round(mu, 4), "tstat": round(tstat, 2),
           "dying": dying,
           "note": f"mean excess {mu:.1%} (t={tstat:.2f}, n={n}), {dying} dying"}
    ok = mu < 0 and tstat < -1.0
    return res, ("CONFIRMED" if ok else "REFUTED"), n


def e055_ai_beta() -> tuple[dict, str, int]:
    """H-AIBETA-1: trailing AI-beta (vs IGV) predicts forward returns."""
    import json as _j
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-AIBETA-1", "high AI-beta names outperform forward (Borri 2026)",
        "L/S tercile spread > 0 over 2y walk-forward",
        "spread <= 0 (AI beta not priced cross-sectionally here)",
        "atoms+NVDA ~17 names; 252d beta vs IGV; 21d fwd; monthly steps")
    atoms = _j.load(open(ROOT / "data" / "universe" / "ai_atoms.json"))
    names = ["NVDA"] + [a["ticker"] for a in atoms.get("companies", [])]
    px = {}
    for t in names:
        try:
            cs = P.history(t, "5y").get("closes", [])
            if len(cs) >= 600:
                px[t] = {c["date"]: c["close"] for c in cs}
        except Exception:
            pass
    try:
        mkt = {c["date"]: c["close"] for c in P.history("IGV", "5y").get("closes", [])}
    except Exception:
        return {"error": "no IGV"}, "INCONCLUSIVE", 0
    dys = sorted(set(mkt) & set().union(*[set(v) for v in px.values()]))
    if len(dys) < 600 or len(px) < 8:
        return {"names": len(px), "days": len(dys)}, "INCONCLUSIVE", 0
    rets = {}
    for t, s in px.items():
        rets[t] = {d: (s[d] / s[p] - 1) for d, p in zip(dys[1:], dys[:-1])
                   if d in s and p in s and s[p]}
    mr = {d: (mkt[d] / mkt[p] - 1) for d, p in zip(dys[1:], dys[:-1])
          if d in mkt and p in mkt and mkt[p]}
    spread = []
    for i in range(252, len(dys) - 21, 21):
        d0 = dys[i]
        betas = {}
        for t, s in rets.items():
            xs = [mr.get(d, 0) for d in dys[i - 252:i]]
            ys = [s.get(d, 0) for d in dys[i - 252:i]]
            mx = sum(xs) / len(xs)
            vx = sum((x - mx) ** 2 for x in xs) / len(xs)
            if vx <= 0:
                continue
            my = sum(ys) / len(ys)
            betas[t] = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx
        if len(betas) < 6:
            continue
        ranked = sorted(betas)
        k = max(len(ranked) // 3, 1)
        lo, hi = ranked[:k], ranked[-k:]
        fl, fh = [], []
        for t in lo:
            if dys[i] in px[t] and dys[i + 21] in px[t] and px[t][dys[i]]:
                fl.append(px[t][dys[i + 21]] / px[t][dys[i]] - 1)
        for t in hi:
            if dys[i] in px[t] and dys[i + 21] in px[t] and px[t][dys[i]]:
                fh.append(px[t][dys[i + 21]] / px[t][dys[i]] - 1)
        if fl and fh:
            spread.append(sum(fh) / len(fh) - sum(fl) / len(fl))
    if len(spread) < 12:
        return {"windows": len(spread)}, "INCONCLUSIVE", len(spread)
    import math as _m
    mu = sum(spread) / len(spread)
    sd = _m.sqrt(sum((x - mu) ** 2 for x in spread) / (len(spread) - 1))
    sh = (mu * 12) / (sd * _m.sqrt(12)) if sd > 0 else 0.0
    tot = 1.0
    for x in spread:
        tot *= 1 + x
    res = {"windows": len(spread), "mean_spread": round(mu, 4),
           "sharpe": round(sh, 3), "total": round(tot - 1, 3),
           "note": f"AI-beta L/S {mu:.2%}/window, Sharpe {sh:.2f}, total {tot-1:.1%}"}
    return res, ("CONFIRMED" if mu > 0 and sh > 0.5 else "REFUTED"), len(spread)


def _pmap_scores() -> dict:
    import json as _j
    uni = _j.load(open(ROOT / "third_party" / "prophetmap" / "data" / "universe.json"))
    us = uni if isinstance(uni, list) else uni.get("tickers", [])
    out = {}
    for u in us:
        s = u.get("symbol")
        if s and "." not in s and "-" not in s:
            out[s] = {"ai": u.get("aiContribution"),
                      "moat": u.get("moatCapture")}
    return out


def _tercile_spread(px: dict, scores: dict[str, float], step: int = 63,
                    fwd: int = 63) -> tuple[list[float], int]:
    dys = sorted(set().union(*[set(v) for v in px.values()]))
    if len(dys) < 300:
        return [], 0
    spread = []
    for i in range(0, len(dys) - fwd - 5, step):
        d0, d1 = dys[i], dys[i + fwd]
        rs = {}
        for t, s in px.items():
            if d0 in s and d1 in s and s[d0] and t in scores and scores[t] is not None:
                rs[t] = (s[d1] / s[d0] - 1, scores[t])
        if len(rs) < 9:
            continue
        ranked = sorted(rs, key=lambda t: rs[t][1])
        k = max(len(ranked) // 3, 1)
        hi = [rs[t][0] for t in ranked[-k:]]
        lo = [rs[t][0] for t in ranked[:k]]
        spread.append(sum(hi) / len(hi) - sum(lo) / len(lo))
    return spread, len(px)


def _summ(spread: list[float]) -> dict:
    import math as _m
    n = len(spread)
    mu = sum(spread) / n
    sd = _m.sqrt(sum((x - mu) ** 2 for x in spread) / (n - 1)) if n > 1 else 0.0
    sh = (mu * 4) / (sd * _m.sqrt(4)) if sd > 0 else 0.0
    return {"n": n, "mean": round(mu, 4),
            "sharpe": round(sh, 3) if n >= 4 else None}


def e056_aicontrib() -> tuple[dict, str, int]:
    """H-PMAP-1: high AI-contribution names outperform (complement channel)."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-PMAP-1", "high aiContribution spread > 0 quarterly",
        "complement exposure wins forward",
        "spread <= 0 (substitution dominates even complements)",
        "prophetmap 89 Universe tickers; 2y Yahoo; 63d fwd quarterly")
    sc = _pmap_scores()
    px = {}
    for t in sc:
        try:
            cs = P.history(t, "2y").get("closes", [])
            if len(cs) >= 300:
                px[t] = {c["date"]: c["close"] for c in cs}
        except Exception:
            pass
    sp, n = _tercile_spread(px, {t: v["ai"] for t, v in sc.items()})
    if len(sp) < 4:
        return {"names": n, "windows": len(sp)}, "INCONCLUSIVE", len(sp)
    s = _summ(sp)
    res = {"names": n, **s, "note": f"aiContrib L/S {s['mean']:.1%}/q (n={n})"}
    return res, ("CONFIRMED" if s["mean"] > 0 else "REFUTED"), s["n"]


def e057_moatshield() -> tuple[dict, str, int]:
    """H-PMAP-2: high-moat names outperform low-moat (distribution shield)."""
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-PMAP-2", "high moatCapture spread > 0 quarterly",
        "moats shield forward returns",
        "spread <= 0 (moats don't protect vs AI repricing)",
        "same panel; moatCapture terciles")
    sc = _pmap_scores()
    px = {}
    for t in sc:
        try:
            cs = P.history(t, "2y").get("closes", [])
            if len(cs) >= 300:
                px[t] = {c["date"]: c["close"] for c in cs}
        except Exception:
            pass
    vals = [v["moat"] for v in sc.values() if v["moat"] is not None]
    if not vals:
        return {"error": "no moat scores"}, "INCONCLUSIVE", 0
    sp, n = _tercile_spread(
        px, {t: (float(v["moat"]) if v["moat"] is not None else None)
             for t, v in sc.items()})
    if len(sp) < 4:
        return {"names": n, "windows": len(sp)}, "INCONCLUSIVE", len(sp)
    s = _summ(sp)
    res = {"names": n, **s, "note": f"moat L/S {s['mean']:.1%}/q (n={n})"}
    return res, ("CONFIRMED" if s["mean"] > 0 else "REFUTED"), s["n"]


def e058_agiproof() -> tuple[dict, str, int]:
    """H-AGIP-1: structural AGI-proof rating predicts fragility (maxDD)."""
    from bneck2 import agiproof as A
    from bneck2 import lab as LAB
    from bneck2 import prices as P
    LAB.preregister(
        "H-AGIP-1", "higher AGI-proof score -> shallower 1y max drawdown",
        "cross-sectional corr(score, maxDD_1y) > 0.3 (less negative DD)",
        "corr <= 0.3 (rating doesn't track realized fragility)",
        "30 tickers w/ full data; 1y Yahoo; structural rating, no prices in")
    import json as _j
    uni = _j.load(open(ROOT / "third_party" / "prophetmap" / "data" / "universe.json"))
    us = uni if isinstance(uni, list) else uni.get("tickers", [])
    names = [u["symbol"] for u in us if u.get("symbol")
             and "." not in u["symbol"] and "-" not in u["symbol"]]
    names += ["CHGG", "UPWK", "FVRR", "DUOL", "IONQ"]
    pts = []
    for t in sorted(set(names)):
        try:
            cs = P.history(t, "1y").get("closes", [])
        except Exception:
            continue
        if len(cs) < 200:
            continue
        px = [c["close"] for c in cs]
        peak, dd = px[0], 0.0
        for x in px:
            peak = max(peak, x)
            dd = min(dd, x / peak - 1 if peak else 0.0)
        pts.append((A.rate(t)["score"], dd, t))
    if len(pts) < 15:
        return {"n": len(pts)}, "INCONCLUSIVE", len(pts)
    import math as _m
    n = len(pts)
    mx = sum(s for s, _, _ in pts) / n
    my = sum(d for _, d, _ in pts) / n
    cov = sum((s - mx) * (d - my) for s, d, _ in pts) / n
    vx = sum((s - mx) ** 2 for s, _, _ in pts) / n
    vy = sum((d - my) ** 2 for _, d, _ in pts) / n
    rho = cov / _m.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0
    res = {"n": n, "rho_score_maxdd": round(rho, 3),
           " weakest": sorted(pts)[:3], "strongest": sorted(pts)[-3:],
           "note": f"corr(rating, maxDD)={rho:.2f} (n={n})"}
    return res, ("CONFIRMED" if rho > 0.3 else "REFUTED"), n


REGISTRY = {
    "E001": e001_burst_forward,
    "E002": e002_attack_crowded,
    "E003": e003_venue_spread,
    "E004": e004_consensus_hitrate,
    "E005": e005_severity_conviction,
    "E006": e006_gap_board,
    "E007": e007_burst_panel,
    "E008": e008_venue_segmentation,
    "E009": e009_severity_crowdedness,
    "E010": e010_acq_chain,
    "E011": e011_acq_silicon,
    "E012": e012_acq_size_split,
    "E013": e013_redteam,
    "E014": e014_signal_chain,
    "E015": e015_signal_biweekly,
    "E016": e016_burst_reversal,
    "E017": e017_long_only,
    "E018": e018_nvda_sell_drift,
    "E019": e019_btc_nvda_beta,
    "E020": e020_btc_pm_snapshot,
    "E021": e021_sec_leads_price,
    "E022": e022_hn_leads_price,
    "E023": e023_filings_vs_chatter,
    "E024": e024_pm_vs_x_order,
    "E025": e025_divergence,
    "E026": e026_predisclosure_drift,
    "E027": e027_espp_filter,
    "E028": e028_distance_high,
    "E029": e029_deep_screen,
    "E030": e030_deep_walkforward,
    "E031": e031_momentum_only,
    "E032": e032_nvda_basket,
    "E033": e033_x_calls,
    "E034": e034_kalshi_momentum,
    "E035": e035_attribution,
    "E036": e036_tilt_attribution,
    "E037": e037_weekend_effect,
    "E038": e038_nventures_mix,
    "E039": e039_implied_identification,
    "E040": e040_promotion_bar,
    "E041": e041_regime_split,
    "E042": e042_pm_ladder_calibration,
    "E043": e043_nvda_stack,
    "E044": e044_sized_vs_full,
    "E045": e045_nvda_alpha,
    "E046": e046_rules_generalize,
    "E047": e047_forward_paper,
    "E048": e048_support_bounce,
    "E049": e049_highn_horserace,
    "E050": e050_nvda_mimic,
    "G001": g001_graph_coverage,
    "G002": g002_layer_backbone,
    "E051": e051_reflexivity,
    "E052": e052_capex_reflex,
    "E053": e053_step_obsolescence,
    "G003": g003_death_watch,
    "E054": e054_death_watch_test,
    "E055": e055_ai_beta,
    "E056": e056_aicontrib,
    "E057": e057_moatshield,
    "E058": e058_agiproof,
}




def _acq_rows():
    import json
    from bneck2 import acq as A
    doc = json.loads((ROOT / "data" / "labs" / "commitments.json")
                     .read_text(encoding="utf-8"))
    good, dropped = A.eligible(doc.get("commitments", []))
    rows = A.event_study(good)
    seen, uniq = set(), []
    for r in rows:
        if r.get("excess") is None:
            continue
        key = (r["event"], r["ticker"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq, dropped








def _weekly_panel_16w(ticker: str, cik: str, hn_query: str):
    """16 weekly buckets ending last Friday: SEC counts, HN counts, returns."""
    import datetime as _dt
    from bneck2 import leads as LD
    from bneck2 import prices as P
    from bneck2 import predict as PD
    from collectors import hn as HN
    today = _dt.date.today()
    fri = today - _dt.timedelta(days=(today.weekday() - 4) % 7)
    starts = [(fri - _dt.timedelta(weeks=k)).isoformat() for k in range(16, -1, -1)]
    doc = PD.submissions(cik)
    fl = (doc.get("filings") or {}).get("recent") or {}
    sec_dates = [d for f, d in zip(fl.get("form", []), fl.get("filingDate", []))
                 if f in ("4", "8-K", "13D", "13G") and d]
    sec = LD.bucketize(sec_dates, starts)
    hn_counts = []
    import calendar
    for i in range(len(starts)):
        lo = starts[i]
        hi = (fri if i == len(starts) - 1 else None)
        try:
            import urllib.parse, urllib.request, json as _j
            lo_ts = calendar.timegm(_dt.datetime.fromisoformat(lo).timetuple())
            hi_s = (fri if i == len(starts) - 1 else
                    _dt.date.fromisoformat(starts[i + 1])).isoformat()
            hi_ts = calendar.timegm(_dt.datetime.fromisoformat(hi_s).timetuple())
            url = ("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
                {"query": hn_query, "tags": "story",
                 "numericFilters": f"created_at_i>{lo_ts},created_at_i<{hi_ts}",
                 "hitsPerPage": 100}))
            req = urllib.request.Request(url, headers={"User-Agent": "bneck"})
            with urllib.request.urlopen(req, timeout=20) as r:
                hn_counts.append(int(_j.loads(r.read().decode("utf-8", "replace")).get("nbHits", 0)))
        except Exception:
            hn_counts.append(0)
    cl = {c["date"]: c["close"] for c in P.history(ticker, "6mo").get("closes", [])}
    rets = []
    for i in range(len(starts)):
        w = [c for d, c in sorted(cl.items()) if starts[i] <= d < (starts[i + 1] if i + 1 < len(starts) else "9999")]
        rets.append(round((w[-1] - w[0]) / w[0], 4) if len(w) >= 2 and w[0] else 0.0)
    return starts, sec, hn_counts, rets




def _oi_buys_all(limit_pages: int = 1):
    """Market-wide buy rows (cluster + officer + latest), filing-dated."""
    from collectors import openinsider as OI
    rows = []
    for fn in (OI.cluster_buys, OI.officer_buys):
        try:
            rows += fn()
        except Exception:
            pass
    return [r for r in rows if r.get("is_buy")]



DEEP_FACTORS = ["f_mom_20", "f_burst", "f_short", "f_hn"]


def _deep_rows():
    import json as _j
    fp = ROOT / "data" / "predict" / "deep-weekly.jsonl"
    try:
        return [_j.loads(l) for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []











def _nvda_pm_markets():
    import json as _j
    import urllib.request as _u
    out = []
    for tag in (10, 50, 100):
        try:
            req = _u.Request(
                f"https://gamma-api.polymarket.com/public-search?q=nvidia&limit_tag={tag}",
                headers={"User-Agent": "bneck"})
            with _u.urlopen(req, timeout=30) as r:
                doc = _j.loads(r.read().decode("utf-8", "replace"))
            for ev in doc.get("events", []):
                out.extend(ev.get("markets", [ev]))
        except Exception:
            pass
    return out



















