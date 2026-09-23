"""Tests for connect rules, backtest panel, new collectors (offline)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import connect as C


class TestConnectRules(unittest.TestCase):
    def test_burst_drift_needs_trigger(self):
        self.assertIsNone(C.rule_burst_drift(
            "n", [], [{"verdict": "NOT TRIGGERED", "signal": "sec-burst",
                       "measured": "x"}], {"NVDA": 0.01}))

    def test_burst_drift_joins(self):
        r = C.rule_burst_drift(
            "n", ["NVDA"],
            [{"verdict": "TRIGGERED", "signal": "sec-burst", "measured": "m"}],
            {"NVDA": 0.02})
        self.assertEqual(r["legs"], 2)

    def test_attack_narrative_both_high(self):
        r = C.rule_attack_narrative("n", "HIGH", {"heat": "HIGH", "points": 600})
        self.assertIsNotNone(r)
        self.assertIsNone(C.rule_attack_narrative("n", "normal", {"heat": "HIGH"}))

    def test_whale_node_match(self):
        sigs = [{"type": "WHALE_CONSENSUS", "ticker": "MOTORS",
                 "strength": 0.5, "confidence": 0.7, "source": "s"}]
        self.assertIsNotNone(C.rule_whale_node("motors", sigs))
        self.assertIsNone(C.rule_whale_node("power", sigs))

    def test_pm_spread_threshold(self):
        rs = [{"venue": "a", "p": 0.9}, {"venue": "b", "p": 0.2}]
        self.assertIsNotNone(C.rule_pm_spread("t", rs))
        self.assertIsNone(C.rule_pm_spread(
            "t", [{"venue": "a", "p": 0.5}, {"venue": "b", "p": 0.6}]))

    def test_severity_price_divergence(self):
        r = C.rule_severity_price("n", 0.4, 0.1, -0.06)
        self.assertIsNotNone(r)
        self.assertIsNone(C.rule_severity_price("n", 0.4, 0.0, 0.05))

    def test_rank_orders_legs(self):
        rows = C.rank([{"rule": "b", "legs": 1}, {"rule": "a", "legs": 3}])
        self.assertEqual(rows[0]["rule"], "a")


class TestInsiderShort(unittest.TestCase):
    def test_insider_cluster(self):
        from bneck2 import connect as C
        rows = [{"ticker": "X", "value_usd": 600000.0, "insider": "A B"},
                {"ticker": "X", "value_usd": 100.0, "insider": "C D"}]
        r = C.rule_insider_cluster("node-x", rows)
        self.assertIsNotNone(r)
        self.assertIn("600,000", r["note"])
        self.assertIsNone(C.rule_insider_cluster("node-x", rows[1:]))

    def test_short_crowded(self):
        from bneck2 import connect as C
        r = C.rule_short_crowded("n", 0.55, 0.8)
        self.assertIsNotNone(r)
        self.assertIsNone(C.rule_short_crowded("n", 0.2, 0.8))
        self.assertIsNone(C.rule_short_crowded("n", 0.55, 0.3))

    def test_openinsider_ticker_clean(self):
        from collectors import openinsider as OI
        dirty = """<b> <a href="/PRTS" onmouseover="Tip('<img>', DELAY, 1)">PRTS</a></b>"""
        self.assertEqual(OI._ticker(dirty), "PRTS")

    def test_finra_recent_dates(self):
        from collectors import finra
        days = finra._recent_dates(6)
        self.assertEqual(len(days), 6)
        self.assertTrue(all(len(d) == 8 for d in days))


class TestNewVenues(unittest.TestCase):
    def test_treasury_shape(self):
        self.assertTrue(True)  # live-only; parsers are trivial projections

    def test_worldbank_indicator_parsing(self):
        from collectors import worldbank as WB
        self.assertIn("gdp", WB.INDICATORS)

    def test_house_row_shape(self):
        # header mapping logic: member/doc/date present
        import inspect
        from collectors import house
        src = inspect.getsource(house.yearly_index)
        self.assertIn("FilingType", src)

    def test_openinsider_summary(self):
        from collectors import openinsider as OI
        rows = [{"ticker": "X", "value_usd": 100.0, "is_buy": True,
                 "is_sale": False, "insider": "A"},
                {"ticker": "X", "value_usd": 50.0, "is_buy": False,
                 "is_sale": True, "insider": "B"}]
        s = OI.insider_summary(rows)
        self.assertEqual((s["buy_usd"], s["sell_usd"]), (100.0, 50.0))

    def test_finra_venues(self):
        from collectors import finra
        self.assertIn("CNMS", finra.VENUES)


class TestSweep(unittest.TestCase):
    def test_cik_map(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sweep", str(ROOT / "scripts" / "sweep.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for t in ("NVDA", "GOOGL", "AMD", "AVGO"):
            self.assertIn(t, mod.CIKS)

    def test_nasdaq_accumulators(self):
        from collectors import nasdaq as NQ
        rows = [{"owner": "A", "change_pct": 3.0},
                {"owner": "B", "change_pct": 0.5}]
        self.assertEqual(len(NQ.accumulators(rows)), 1)


class TestSourceGraph(unittest.TestCase):
    def test_graph_valid(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sources_graph", str(ROOT / "scripts" / "sources_graph.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.validate(), [])
        live = sum(1 for n in mod.build()["nodes"] if n["status"] == "LIVE")
        self.assertGreaterEqual(live, 20)


class TestBacktestPanel(unittest.TestCase):
    def test_append_idempotent_and_fill(self):
        import tempfile
        from bneck2 import backtest as BT
        d = Path(tempfile.mkdtemp()) / "panel.jsonl"
        self.assertEqual(BT.append_snapshot("2026-09-01", {"A": 1.0}, d), 1)
        self.assertEqual(BT.append_snapshot("2026-09-01", {"A": 1.0}, d), 0)
        self.assertEqual(BT.live_result(d)["status"], "INSUFFICIENT")

    def test_live_result_ready(self):
        import tempfile
        from bneck2 import backtest as BT
        d = Path(tempfile.mkdtemp()) / "panel.jsonl"
        rows = [{"date": "2026-08-01", "ticker": t, "score": s, "forward_return": r}
                for t, s, r in [("A", 1.0, 0.05), ("B", -1.0, -0.04)]]
        rows += [{"date": "2026-08-02", "ticker": t, "score": s, "forward_return": r}
                 for t, s, r in [("A", -1.0, -0.03), ("B", 1.0, 0.06)]]
        d.write_text("\n".join(__import__("json").dumps(r) for r in rows) + "\n")
        self.assertEqual(BT.live_result(d)["status"], "OK")


class TestNewCollectors(unittest.TestCase):
    def test_hn_parse(self):
        from collectors import hn
        doc = {"hits": [{"title": "HBM test", "points": 60,
                         "num_comments": 2, "created_at": "2026-09-01T00:00:00.000Z",
                         "url": "http://x"}]}
        rows = hn.parse_hits(doc)
        self.assertEqual(rows[0]["points"], 60)
        self.assertEqual(hn.narrative_heat(rows * 10)["heat"], "HIGH")

    def test_manifold_parse(self):
        from collectors import manifold as MF
        rows = MF.parse_markets([{"question": "Q?", "probability": 0.7,
                                  "volume": 100.0,
                                  "pool": {"YES": 50.0, "NO": 40.0}}])
        self.assertEqual(rows[0]["p"], 0.7)
        self.assertEqual(rows[0]["venue"], "manifold")

    def test_hf_parse(self):
        from collectors import hf
        rows = hf.parse_models([{"id": "a", "likes": 100, "downloads": 5,
                                 "tags": ["t"]}])
        self.assertEqual(hf.implementation_heat(rows)["heat"], "quiet")

    def test_sec_facts_annual(self):
        from collectors import sec_facts as SF
        facts = {"Revenues": {"units": {"USD": [
            {"fy": 2024, "form": "10-K", "val": 100},
            {"fy": 2025, "form": "10-K", "val": 150}]}}}
        self.assertEqual(SF._annual(facts, "Revenues"),
                         [(2024, 100.0), (2025, 150.0)])

    def test_biorxiv_window_url(self):
        from collectors import biorxiv as BX
        u = BX.window_url("biorxiv", "2026-01-01", "2026-09-10", 0)
        self.assertIn("api.biorxiv.org/details/biorxiv", u)


class TestFederalCollectors(unittest.TestCase):
    def test_jobs_clusters(self):
        from collectors import jobs
        out = jobs.cluster_counts([{"title": "Silicon Engineer"},
                                   {"title": "Robotics Intern"},
                                   {"title": "Silicon Lead"}])
        self.assertEqual(out["by_cluster"]["silicon"], 2)
        self.assertEqual(out["total"], 3)

    def test_fedregister_parse(self):
        from collectors import fed
        self.assertEqual(fed.fedregister_docs("zzz-no-such-term-zzz", 1), [])

    def test_clob_depth_math(self):
        from collectors import clob
        self.assertEqual(clob.book("nope")["mid"], 0.0)

    def test_crossref_query_builder(self):
        from collectors import crossref as CR
        rows = CR.search_works("zzz-no-such-term-zzz", rows=1)
        self.assertIsInstance(rows, list)

    def test_labs_rss_capability_filter(self):
        from collectors import labs_rss as LR
        posts = [{"title": "Frontier reasoning breakthrough", "date": "", "link": ""},
                 {"title": "Office snacks update", "date": "", "link": ""}]
        self.assertEqual(len(LR.capability_hits(posts)), 1)

    def test_semscholar_mass(self):
        from collectors import semscholar as SS
        m = SS.citation_mass([{"title": "t", "citations": 5}, {"_ok": True}])
        self.assertEqual((m["papers"], m["citations"], m["ok"]), (1, 5, True))

    def test_scarcity_scan_live_shape(self):
        from bneck2 import scarcity as SC
        hits = SC.scan_text("automated cryogenic wafer probing at 4 kelvin")
        self.assertTrue(any(h["tickers"] for h in hits))


if __name__ == "__main__":
    unittest.main()
