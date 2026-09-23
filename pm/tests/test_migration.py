"""bneck2 migration tests — severity, velocity, cross-world X, release,
catalytic hazards, derivatives, alpha_v2, consistency, transfer tiers."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import consistency as CY
from bneck2 import migration as M


class TestSeverity(unittest.TestCase):
    NODE = {"id": "memory_hbm", "revenue_purity": 0.8, "td_years": 3.0}

    def test_formula(self):
        s = M.severity(self.NODE, {"demand_growth": 2.0})
        # 2.0*0.8*0.3*(0.5+0.25)/0.5 = 0.72
        self.assertAlmostEqual(s["B"], 0.72, places=3)
        self.assertTrue(s["permission_estimated"])

    def test_permission_prior(self):
        s = M.severity({"id": "power", "revenue_purity": 0.5, "td_years": 10.0})
        self.assertEqual(s["permission"], 0.85)

    def test_explicit_field_not_estimated(self):
        s = M.severity({"id": "x", "permission_friction": 0.9,
                        "revenue_purity": 0.5, "td_years": 5.0})
        self.assertFalse(s["permission_estimated"])


class TestVelocity(unittest.TestCase):
    def test_needs_two_points(self):
        self.assertEqual(M.velocity("n", [])["n"], 0)

    def test_growth_and_accel(self):
        h = [{"node_id": "n", "B": 1.0, "ts": "2026-01-01T00:00:00Z"},
             {"node_id": "n", "B": 2.0, "ts": "2026-07-01T00:00:00Z"},
             {"node_id": "n", "B": 4.0, "ts": "2027-01-01T00:00:00Z"}]
        v = M.velocity("n", h)
        self.assertGreater(v["dB_dt"], 0)
        self.assertGreater(v["accel"], 0)


class TestCrossWorld(unittest.TestCase):
    def test_exposure(self):
        inc = {"id": "bpo", "survives": {"w1": 0.2, "w2": 1.0}}
        worlds = [{"id": "w1", "p_you": 0.5}, {"id": "w2", "p_you": 0.5}]
        x = M.cross_world_exposure(inc, worlds)
        self.assertAlmostEqual(x["X"], 0.4)


class TestRelease(unittest.TestCase):
    def test_laplace_no_data(self):
        r = M.release_probability("n", [])
        self.assertEqual(r["P_release"], 0.5)

    def test_supply_only(self):
        obs = [{"node_id": "n", "signal": "capacity adds",
                "measured": "cap +20%", "verdict": "TRIGGERED"}]
        r = M.release_probability("n", obs)
        self.assertGreater(r["P_release"], 0.5)


class TestCatalytic(unittest.TestCase):
    def test_hazard_update(self):
        self.assertAlmostEqual(
            M.hazard_update(0.1, [{"strength": 1.0, "event": 1.0}]), 0.2)

    def test_catalytic_filter(self):
        g = {"edges": [{"relation": "DEPENDS_ON"}, {"relation": "CATALYZES"}]}
        self.assertEqual(len(M.catalytic_edges(g)), 1)


class TestDerivative(unittest.TestCase):
    G = {"edges": [
        {"source": "accelerators", "target": "memory_hbm",
         "relation": "DEPENDS_ON"},
        {"source": "memory_hbm", "target": "memory_dram",
         "relation": "CASCADE"}]}

    def test_dependents_and_unlocks(self):
        d = M.bottleneck_derivative("memory_hbm", self.G)
        by = {r["node"]: r["via"] for r in d}
        self.assertEqual(by["accelerators"], "dependent-surge")
        self.assertEqual(by["memory_dram"], "cascade-unlock")


class TestAlphaV2(unittest.TestCase):
    def test_master_equation(self):
        self.assertAlmostEqual(M.alpha_v2(0.5, 1e9, 0.4, 0.7, 0.8, 0.3),
                               0.5 * 1e9 * 0.4 * 0.7 * 0.8 - 0.3)


class TestConsistency(unittest.TestCase):
    DOC = {"worlds": [{"id": "w1", "p_you": 0.1, "p_market": 0.8}],
             "incumbents": [{"id": "bpo", "survives": {"w1": 0.1},
                             "market_survival_p": 0.9}]}

    def test_finds_contradiction(self):
        rows = CY.find_inconsistencies(self.DOC)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["score"], 0.8 * 0.8, places=3)

    def test_render(self):
        self.assertIn("bpo", CY.render(CY.find_inconsistencies(self.DOC)))

    def test_quiet_when_consistent(self):
        doc = {"worlds": [{"id": "w1", "p_you": 0.8, "p_market": 0.8}],
               "incumbents": [{"id": "b", "survives": {"w1": 0.9},
                               "market_survival_p": 0.9}]}
        self.assertEqual(CY.find_inconsistencies(doc), [])


class TestTransfer(unittest.TestCase):
    def test_benchmarks_low(self):
        self.assertLess(M.transfer_weight("benchmark"),
                        M.transfer_weight("verified_cashflow"))
        self.assertEqual(M.transfer_weight("unknown-kind"), 0.5)


class TestGoatedPrimitives(unittest.TestCase):
    def test_deliverable_mw(self):
        d = M.deliverable_mw(5000.0, {"site": 1.0, "interconnect": 0.5,
                                      "transformer": 0.8, "generation": 1.0,
                                      "permit": 0.9})
        self.assertAlmostEqual(d["deliverable_mw"], 5000 * 0.36)
        self.assertEqual(d["estimated_legs"], [])

    def test_deliverable_flags_missing(self):
        d = M.deliverable_mw(100.0, {})
        self.assertEqual(len(d["estimated_legs"]), 5)

    def test_surprise_moves_toward_evidence(self):
        up = M.surprise_update(0.5, 2.0, 1.0)
        self.assertGreater(up["posterior"], 0.5)
        flat = M.surprise_update(0.5, 2.0, 0.0)
        self.assertAlmostEqual(flat["posterior"], 0.5)

    def test_cliff(self):
        self.assertTrue(M.cliff_proximity("assay_sample_usd", 0.5)["crossed"])
        self.assertFalse(M.cliff_proximity("assay_sample_usd", 50.0)["crossed"])
        self.assertIsNone(M.cliff_proximity("nope", 1.0)["proximity"])

    def test_duration_mismatch(self):
        self.assertEqual(
            M.duration_mismatch(6.0, 2.0)["verdict"], "SHORT_CANDIDATE")
        self.assertEqual(M.duration_mismatch(6.0, None)["verdict"],
                         "INSUFFICIENT")
        self.assertEqual(M.tech_half_life(4.0), 2.0)


class TestAtoms(unittest.TestCase):
    def test_universe_loads(self):
        from bneck2 import atoms as A
        cos = A.load_universe()
        self.assertGreaterEqual(len(cos), 10)
        self.assertTrue(all(c.get("ticker") and c.get("nodes") for c in cos))

    def test_small_critical_outranks_giant(self):
        from bneck2 import atoms as A
        cos = [{"ticker": "LPKF-like", "layer": "t", "nodes": ["n1"],
                "rev_usd_m": 125},
               {"ticker": "GIANT", "layer": "t", "nodes": ["n1"],
                "rev_usd_m": 100000}]
        rows = A.screen(cos, severity_by_node={"n1": 1.0})
        self.assertEqual(rows[0]["ticker"], "LPKF-like")

    def test_breadth_bonus(self):
        from bneck2 import atoms as A
        one = {"ticker": "A", "layer": "t", "nodes": ["n1"], "rev_usd_m": 500}
        two = {"ticker": "B", "layer": "t", "nodes": ["n1", "n2"],
               "rev_usd_m": 500}
        sev = {"n1": 1.0, "n2": 1.0}
        self.assertGreater(A.convexity(two, sev)["convexity"],
                           A.convexity(one, sev)["convexity"])


class TestPredict(unittest.TestCase):
    def test_spearman(self):
        from bneck2 import predict as PD
        self.assertAlmostEqual(
            PD.spearman([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 4.0, 5.0]), 1.0)
        self.assertIsNone(PD.spearman([1.0, 1.0], [1.0, 2.0]))
        self.assertIsNone(PD.spearman([1.0], [1.0]))

    def test_grid_shapes(self):
        from bneck2 import predict as PD
        self.assertEqual(len(PD.grid("monthly", 12)), 12)
        self.assertEqual(len(PD.grid("biweekly", 12)), 24)

    def test_composite_by_date_no_leak(self):
        from bneck2 import predict as PD
        rows = [{"date": "2026-01-01", "ticker": t, "f": float(i),
                 "fwd_20": 0.01} for i, t in enumerate("ABCD")]
        rows += [{"date": "2026-02-01", "ticker": t, "f": 100.0 + i,
                  "fwd_20": 0.01} for i, t in enumerate("ABCD")]
        out = PD.composite_by_date(rows, ["f"], {"f": 1.0})
        jan = sorted(r["score"] for r in out if r["date"] == "2026-01-01")
        feb = sorted(r["score"] for r in out if r["date"] == "2026-02-01")
        # identical within-date ranks despite level shift => per-date norms
        self.assertEqual([round(x, 3) for x in jan], [round(x, 3) for x in feb])

    def test_trailing_forward(self):
        from bneck2 import predict as PD
        cl = [(f"2026-01-{d:02d}", 100.0 + d) for d in range(1, 15)]
        self.assertAlmostEqual(PD.trailing_return(cl, "2026-01-14", 5), 5 / 109, places=3)
        self.assertIsNone(PD.forward_return(cl, "2026-01-14", 5))


class TestDeep(unittest.TestCase):
    def test_biweekly_grid_count(self):
        from bneck2 import predict as PD
        g = PD.grid("biweekly", 12)
        self.assertEqual(len(g), 24)
        self.assertTrue(all(g[i] < g[i + 1] for i in range(len(g) - 1)))

    def test_submissions_cached(self):
        from bneck2 import predict as PD
        PD._SUBMISSIONS_CACHE["TEST"] = {"cached": True}
        self.assertEqual(PD.submissions("TEST"), {"cached": True})
        del PD._SUBMISSIONS_CACHE["TEST"]

    def test_shift(self):
        from bneck2 import predict as PD
        self.assertEqual(PD._shift("2026-09-10", -30), "2026-08-11")

    def test_finra_cache_file(self):
        from collectors import finra
        import tempfile
        self.assertTrue(callable(finra.short_file))


class TestTournament(unittest.TestCase):
    def test_round_deterministic(self):
        import json
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tournament", str(ROOT / "scripts" / "tournament.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r1 = json.loads((ROOT / "data" / "tournament" / "r1" / "results.json").read_text())
        r2 = json.loads((ROOT / "data" / "tournament" / "r1.1" / "results.json").read_text())
        self.assertEqual(
            [(s["id"], s["verdict"]) for s in r1["seeds"] if s["verdict"] == "PROMOTE"],
            [("seed1.conv", "PROMOTE"), ("seed1.B", "PROMOTE")])
        muts = json.loads((ROOT / "data" / "tournament" / "r1.1" / "mutations.json").read_text())
        self.assertTrue(all("why" in m for m in muts))
        kept = {s["id"] for s in r2["seeds"]}
        self.assertTrue({"seed1.1.conv", "seed1.1.B"} <= kept)


class TestReasonBandit(unittest.TestCase):
    def test_pick_and_record(self):
        from bneck2 import reason
        doc = {a: {"pulls": 0, "reward": 0.0} for a in reason.ARMS}
        self.assertIn(reason.pick(doc, seed=1), reason.ARMS)
        doc = reason.record("causal", 2.0, dict(doc))
        self.assertEqual(doc["causal"], {"pulls": 1, "reward": 2.0})
        self.assertEqual(len(reason.PROMPTS), 6)

    def test_rediscovery_file(self):
        import json as _j
        rows = _j.loads(Path("/home/ubuntu/bneck2/experimentation/rediscovery.json").read_text())
        self.assertEqual(len(rows), 3)
        self.assertTrue(all("check" in r for r in rows))


class TestEdges(unittest.TestCase):
    def test_blank_unknowns(self):
        from bneck2 import edges as E
        e = E.blank_edge("A", "B")
        self.assertIsNone(e["supply"]["lead_time_months"])
        self.assertEqual(e["grade"], "HYPOTHESIS")

    def test_evidence_grading(self):
        from bneck2 import edges as E
        e = E.blank_edge("A", "B")
        e = E.add_evidence(e, "120 weeks", "Eaton ER", "2026-08-01", 0.7)
        self.assertEqual(e["grade"], "SUPPORTED")
        e["supply"]["lead_time_months"] = 30
        e = E.add_evidence(e, "2nd source", "ABB ER", "2026-08-05", 0.6)
        self.assertEqual(e["grade"], "QUANTIFIED")

    def test_promote_blocked_without_evidence(self):
        from bneck2 import edges as E
        E.propose(E.blank_edge("TEST_A", "TEST_B"))
        r = E.promote("TEST_A", "TEST_B", "REQUIRES")
        self.assertIn("error", r)
        cands = __import__("json").loads(E.QUARANTINE.read_text())
        cands = [c for c in cands if c["source"] != "TEST_A"]
        E.QUARANTINE.write_text(__import__("json").dumps(cands, indent=1))

    def test_observation(self):
        from bneck2 import observation as O
        o = O.observe("HV_TRANSFORMER", "lead_time_mention", "120",
                      "2026-08-01", "Eaton ER", 0.7)
        r = O.route(o)
        self.assertEqual(r["route"], "edge.supply.lead_time_months")
        m = O.motion([dict(o, object="100"), dict(o, object="120")])
        self.assertEqual(m["delta"], 20.0)
        import json
        reg = json.load(open("data/universe/actor_registry.json"))
        self.assertGreaterEqual(len(reg["actors"]), 30)
        self.assertEqual(reg["meta"]["status"], "seed-unverified")

    def test_fy_series(self):
        from bneck2 import experiments as X
        facts = {"facts": {"us-gaap": {"ResearchAndDevelopmentExpense": {
            "units": {"USD": [
                {"fy": 2022, "val": 100, "form": "10-K", "end": "2022-12-31"},
                {"fy": 2023, "val": 120, "form": "10-K", "end": "2023-12-31"},
                {"fy": 2023, "val": 5, "form": "10-Q", "end": "2023-09-30"}]}}}}}
        s, m = X._fy_series(facts, "ResearchAndDevelopmentExpense")
        self.assertEqual(s, [(2022, 100.0), (2023, 120.0)])
        self.assertEqual(m, 12)

    def test_edge_update_pure(self):
        from bneck2 import edge_update as U
        g = {"nodes": [{"id": "N", "crowdedness": 0.5,
                        "suppliers": [{"ticker": "X", "evidence": []}],
                        "evidence": []}]}
        g2, m = U.short_to_crowdedness(g, {"X": 0.40}, "2026-09-10")
        self.assertEqual(g2["nodes"][0]["crowdedness"], 0.5)
        self.assertEqual(len(m), 1)
        g3, m3 = U.short_to_crowdedness(
            {"nodes": [{"id": "N", "suppliers": []}]}, {"X": 0.4}, "2026-09-10")
        self.assertEqual(m3, [])

    def test_filings_burst(self):
        from bneck2 import edge_update as U
        g = {"nodes": [{"id": "N",
                        "suppliers": [{"ticker": "Y", "evidence": []}],
                        "evidence": []}]}
        _, m = U.filings_to_suppliers(
            g, {"Y": {"form4": 12, "deal": 1, "base4": 3}}, "2026-09-10")
        self.assertEqual(len(m), 1)
        _, m2 = U.filings_to_suppliers(
            g, {"Y": {"form4": 2, "deal": 0, "base4": 3}}, "2026-09-10")
        self.assertEqual(m2, [])

    def test_attribution_pure(self):
        from bneck2 import attribution as A
        xs = [float(i) for i in range(12)]
        self.assertEqual(A._r2(xs, xs), 1.0)
        self.assertEqual(A._r2([1, 1, 1], [1, 2, 3]), 0.0)
        for got, exp in zip(A._rets([100.0, 110.0, 99.0]), [0.1, -0.1]):
            self.assertAlmostEqual(got, exp)
        a = A.attribute("NOPE")
        self.assertIn("error", a)
        panel = A.load_panel()
        self.assertGreaterEqual(len(panel), 80)

    def test_agiproof(self):
        from bneck2 import agiproof as A
        c = A.rate("CHGG")
        self.assertEqual(c["grade"], "F")
        n = A.rate("NVDA")
        self.assertGreater(n["score"], c["score"])
        b = A.board(["CHGG", "NVDA"])
        self.assertEqual(b[0]["ticker"], "CHGG")

    def test_concepts(self):
        from bneck2 import concepts as C
        r = C.concept_report("optics")
        self.assertGreaterEqual(r["suppliers"], 3)
        rel = [x["reliance"] for x in r["crash_rank"]]
        self.assertEqual(rel, sorted(rel, reverse=True))
        self.assertIn("memory", C.CONCEPT_GROUPS)

    def test_bearcase_boolean(self):
        from bneck2 import bearcase as B
        doc = {"trees": {"T": [{"id": "a", "w": 3, "poll": "manual", "q": "x"},
                               {"id": "b", "w": 1, "poll": "price_vs_high",
                                "ticker": "T", "below": 0.7, "q": "y"}]},
               "states": {"T": {"a": {"value": True, "source": "t"}}}}
        out = B.evaluate(doc, {})
        self.assertEqual(out["T"]["p_bear"], 1.0)
        self.assertEqual(out["T"]["coverage"], 0.75)
        import datetime as _dt
        base = _dt.date(2024, 1, 1)
        px = {"T": {(base + _dt.timedelta(days=i)).isoformat(): 100.0
                    for i in range(250)}}
        out2 = B.evaluate(doc, px)
        self.assertEqual(out2["T"]["p_bear"], 0.75)
        self.assertIsNone(B.poll_price({"ticker": "ZZ"}, {}))

    def test_target_workup(self):
        import json
        import subprocess
        r = subprocess.run(["python3", "scripts/work_target.py", "MRVL"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        w = json.load(open("data/bottlenecks/workup_MRVL.json"))
        self.assertEqual(w["ticker"], "MRVL")
        self.assertTrue(w["layers"])
        self.assertIn(w["verdict"], ("OVERLOADED-LONG-AT-RISK", "THREATENED",
                                     "STRUCTURAL", "UNKNOWN"))

    def test_death_watch_ranked(self):
        import json as _j
        from bneck2 import propagate as P
        d = P.death_watch()
        self.assertGreaterEqual(len(d["watch"]), 10)
        tickers = [w["ticker"] for w in d["watch"]]
        self.assertIn("SKHY", tickers)
        ov = _j.load(open("data/bottlenecks/threat_graph.json"))
        self.assertTrue(any(e["target"] == "CO_AAOI" for e in ov["edges"]))
        import json
        qf = _j.load(open("data/bottlenecks/threat_queue.json"))
        self.assertIn("queue", qf)
        self.assertGreaterEqual(len(qf["queue"]), 20)
        for r in qf["queue"]:
            self.assertIn(r["status"], ("DYING", "UNPRICED", "QUESTIONED", "NO-DATA"))

    def test_threat_overlay(self):
        import json
        import subprocess
        r = subprocess.run(["python3", "scripts/threat_extract.py"],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        ov = json.load(open("data/bottlenecks/threat_graph.json"))
        self.assertGreaterEqual(len(ov["edges"]), 10)
        for e in ov["edges"]:
            self.assertEqual(e["relation"], "THREATENS")
            self.assertTrue(e["evidence"])

    def test_propagate_spreads(self):
        from bneck2 import propagate as P
        g = {"nodes": [{"id": "A"}, {"id": "B"}],
             "edges": [{"source": "A", "target": "B", "relation": "REQUIRES",
                        "grade": "SUPPORTED"}]}
        s = P.propagate(g, {"A": 1.0})
        self.assertEqual(s["A"], 1.0)
        self.assertGreater(s["B"], 0.0)

    def test_prophetmap_backbone(self):
        import json
        import subprocess
        r = subprocess.run(["python3", "scripts/prophetmap_import.py"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        g = json.load(open("data/bottlenecks/graph_v2.json"))
        pml = [n for n in g["nodes"] if n["id"].startswith("PML_")]
        self.assertGreaterEqual(len(pml), 25)
        for n in pml:
            self.assertNotIn("tickers", n)

    def test_highlevel_watchlist(self):
        import json
        d = json.load(open("data/universe/highlevel_watchlist.json"))
        self.assertGreaterEqual(len(d["candidates"]), 25)
        self.assertGreaterEqual(len(d["primitives"]), 10)
        for c in d["candidates"]:
            self.assertIn("status", c)
            self.assertIn("memo", c)

    def test_coverage_keys(self):
        from bneck2 import edges as E
        c = E.coverage()
        for k in ("edges", "with_evidence", "quantified",
                  "pct_evidence", "pct_quantified"):
            self.assertIn(k, c)


class TestNvda(unittest.TestCase):
    def test_size_bounds(self):
        from bneck2 import nvda as NV
        for mode in ("mom", "burst_fade", "short_fade", "combo",
                     "buyhold3x", "buyhold1x"):
            w = NV.size_rule({"mom_20": 0.2, "burst": 1.0, "short": 0.4,
                              "hn": 3}, mode)
            self.assertGreaterEqual(w, -1.0)
            self.assertLessEqual(w, 3.0)

    def test_paper_log(self):
        import subprocess
        r = subprocess.run(["python3", "scripts/paper.py"], capture_output=True,
                           text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        import csv
        rows = list(csv.DictReader(
            open("data/paper/nvda.csv")))
        self.assertGreaterEqual(len(rows), 1)


class TestAdvise(unittest.TestCase):
    def test_confidence_map(self):
        from bneck2 import advise as AD
        self.assertEqual(AD.confidence_from_lower(0.5), 0.0)
        self.assertEqual(AD.confidence_from_lower(0.75), 1.0)
        self.assertEqual(AD.confidence_from_lower(0.9), 1.0)

    def test_dust_filter(self):
        from bneck2 import advise as AD
        self.assertEqual(AD.advise(0.5, 0.1)["action"], "HOLD")
        a = AD.advise(-0.8, 0.5)
        self.assertEqual((a["action"], a["fraction"]), ("SELL", 0.4))

    def test_buyback(self):
        from bneck2 import advise as AD
        self.assertTrue(AD.buyback_trigger(100, 90, 0.5, -0.5)["rebuy"])
        self.assertFalse(AD.buyback_trigger(100, 110, -0.5, -0.5)["rebuy"])

    def test_sequence(self):
        from bneck2 import advise as AD
        s = AD.sequence_update(None, {"action": "SELL", "fraction": 0.6}, 100)
        self.assertEqual(s["state"], "SHORT-WATCH")
        s2 = AD.sequence_update(s, {"action": "HOLD", "fraction": 0.0}, 101)
        self.assertEqual(len(s2["history"]), 2)


class TestFocusedNames(unittest.TestCase):
    def test_kalshi_series_fields(self):
        from collectors import kalshi as KL
        doc = {"events": [{"title": "T", "series_ticker": "KX",
                           "markets": [{"ticker": "KX-1", "last_price_dollars": "0.4",
                                        "volume_24h_fp": "5", "liquidity_dollars": "6"}]}]}
        rows = KL.parse_events(doc, "whatever txyz")
        self.assertEqual(rows, [])

    def test_universe_expanded(self):
        from bneck2 import predict as PD
        self.assertGreaterEqual(len(PD.UNIVERSE), 25)
        for t in ("ONTO", "SNPS", "TSM"):
            self.assertIn(t, PD.UNIVERSE)

    def test_registry_has_focus(self):
        from bneck2 import experiments as X
        for e in ("E018", "E019", "E020", "E021", "E022", "E023",
                  "E024", "E025", "E026", "E027", "E028", "E032", "E033",
                  "E034", "E035", "E036", "E037", "E038", "E039", "E040", "E041",
                  "E042", "E043", "E044", "E045", "E046", "E047", "E048", "E049", "E050", "E051", "E052", "E053", "E054", "E055", "E056", "E057", "E058", "G001", "G002", "G003"):
            self.assertIn(e, X.REGISTRY)

    def test_crypto_history_shape(self):
        from bneck2 import prices as P
        h = P.crypto_history("bitcoin", 7)
        self.assertIn("closes", h)
        if h["closes"]:
            self.assertIn("date", h["closes"][0])

    def test_xextract_classify(self):
        from bneck2 import xextract as XE
        c = XE.classify("Long $NVDA into earnings, target $250")
        self.assertEqual(c["direction"], "LONG")
        self.assertIn("NVDA", c["tickers"])
        c2 = XE.classify("nice weather today, markets closed")
        self.assertEqual(c2["kind"], "COMMENTARY")
        d = XE.density([{"text": "long NVDA", "isReply": False},
                        {"text": "hello", "isReply": True}])
        self.assertEqual(d["n"], 1)

    def test_alog_appends(self):
        import tempfile
        from bneck2 import lab as LAB
        old_dir = LAB.ALOG
        LAB.ALOG = Path(tempfile.mkdtemp())
        try:
            r = LAB.alog("TEST", "hello")
            self.assertEqual(r["task"], "TEST")
            self.assertTrue(r["ts"].startswith("2026"))
            self.assertTrue((LAB.ALOG / "a-log.jsonl").exists())
        finally:
            LAB.ALOG = old_dir

    def test_secret_gate(self):
        import subprocess
        r = subprocess.run(["bash", str(ROOT / "scripts" / "check_secrets.sh")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout[-500:])

    def test_beta_math(self):
        br = [0.01, -0.02, 0.03]
        nr = [0.02, -0.04, 0.06]
        mb, mn = sum(br) / 3, sum(nr) / 3
        beta = sum((b - mb) * (n - mn) for b, n in zip(br, nr)) / sum((b - mb) ** 2 for b in br)
        self.assertAlmostEqual(beta, 2.0)


class TestLeads(unittest.TestCase):
    def test_xcorr_peak(self):
        from bneck2 import leads as LD
        x = [0, 0, 0, 1.0, 0, 0, 0, 0, 0, 0]
        y = [0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0]
        ll = LD.lead_lag(x, y, max_lag=4)
        self.assertEqual(ll["peak_lag"], 2)
        self.assertGreater((ll["peak_r"] or 0), 0.5)

    def test_insufficient(self):
        from bneck2 import leads as LD
        ll = LD.lead_lag([1.0], [1.0])
        self.assertEqual(ll["verdict"], "INSUFFICIENT")

    def test_bucketize(self):
        from bneck2 import leads as LD
        starts = ["2026-01-01", "2026-01-08", "2026-01-15"]
        self.assertEqual(LD.bucketize(["2026-01-02", "2026-01-09", "2026-01-09"], starts), [1, 2, 0])


class TestAcq(unittest.TestCase):
    def test_map_and_eligible(self):
        from bneck2 import acq as A
        self.assertEqual(A.map_tickers("OpenAI", "AMD GPUs 6 GW"), ["AMD"])
        self.assertEqual(A.map_tickers("OpenAI", "Cerebras"), [])
        good, dropped = A.eligible([
            {"date": "2026-01-01", "lab": "x", "target": "y", "kind": "k"},
            {"date": "2026-04-06", "lab": "Anthropic",
             "target": "Google/Broadcom", "kind": "deployment"},
            {"date": "2026-01-14", "lab": "OpenAI", "target": "Cerebras",
             "kind": "deployment"}])
        self.assertEqual(len(good), 1)
        self.assertEqual(
            {d["reason"] for d in dropped},
            {"placeholder-date", "private-or-ambiguous-target"})

    def test_summarize_gates(self):
        from bneck2 import acq as A
        rows = [{"excess": 0.20}, {"excess": 0.01},
                {"excess": -0.01}, {"excess": 0.30}, {"excess": 0.10}]
        s = A.summarize(rows)
        self.assertEqual(s["verdict"], "CONFIRMED")
        self.assertEqual(A.summarize([{"excess": None}])["verdict"],
                         "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()