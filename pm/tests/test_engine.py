"""bneck tests — stdlib unittest, no network, no deps.

Run: /usr/bin/python3 -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import graph as G
from bneck2 import quant as Q


class TestGraphV2Schema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = G.load_graph()

    def test_required_node_fields(self):
        required = {"id", "label", "status", "prevalence", "crowdedness",
                    "constraint_class", "tk_years", "td_years"}
        for n in self.g["nodes"]:
            self.assertTrue(required <= set(n), f"{n.get('id')} missing fields")

    def test_edges_reference_nodes(self):
        ids = {n["id"] for n in self.g["nodes"]}
        for e in self.g.get("edges", []):
            self.assertIn(e["source"], ids)
            self.assertIn(e["target"], ids)

    def test_temporal_edge_fields(self):
        for e in self.g.get("edges", []):
            for f in ("relation", "valid_from", "confidence"):
                self.assertIn(f, e)

    def test_new_relations_present(self):
        rels = {e["relation"] for e in self.g.get("edges", [])}
        self.assertIn("PATENT_COVERED_BY", rels)
        self.assertIn("REGULATED_BY", rels)


class TestScoring(unittest.TestCase):
    def test_conviction_weights(self):
        n = {"prevalence": 1.0, "crowdedness": 0.0, "evidence": ["a"] * 10}
        self.assertAlmostEqual(G.score_node(n), 0.5 + 0.3 + 0.2)

    def test_short_only_binding(self):
        n = {"status": "emerging", "crowdedness": 0.9, "kill_signals": ["k"]}
        self.assertEqual(G.short_score(n, ["k"]), 0.0)
        b = {"status": "binding", "crowdedness": 0.8, "kill_signals": ["k1", "k2"]}
        self.assertAlmostEqual(G.short_score(b, []), 0.8 * 0.3)
        self.assertAlmostEqual(G.short_score(b, ["k1", "k2"]), 0.8 * 1.0)
        self.assertGreater(G.short_score(b, ["k1", "k2"]), G.short_score(b, ["k1"]))

    def test_rebalance_ladder(self):
        self.assertTrue(G.rebalance_action({"status": "solved"}, 0).startswith("EXIT"))
        self.assertTrue(G.rebalance_action(
            {"status": "binding", "crowdedness": 0.2}, 0.6).startswith("OVERWEIGHT"))
        self.assertTrue(G.rebalance_action(
            {"status": "binding", "crowdedness": 0.9}, 0.6).startswith("HOLD"))
        self.assertTrue(G.rebalance_action(
            {"status": "emerging", "crowdedness": 0.2}, 0.6).startswith("ACCUMULATE"))


class TestQuant(unittest.TestCase):
    def test_tk_td_signals(self):
        self.assertEqual(Q.tk_td({"tk_years": 8, "td_years": 2})["signal"], "LONG-WINDOW")
        self.assertEqual(Q.tk_td({"tk_years": 1, "td_years": 5})["signal"], "CLOSING")
        self.assertEqual(Q.tk_td({"tk_years": 5, "td_years": 3})["signal"], "MID")
        self.assertEqual(Q.tk_td({})["signal"], "UNKNOWN")

    def test_redundancy_convexity_ordering(self):
        lo = {"agi_p": 0.1, "deploy_p": 0.2, "revenue_purity": 0.2,
              "op_leverage": 1.0, "expect_years": 2.0, "crowdedness": 0.2}
        hi = {"agi_p": 0.8, "deploy_p": 0.9, "revenue_purity": 0.9,
              "op_leverage": 2.0, "expect_years": 10.0, "crowdedness": 0.9}
        self.assertGreater(Q.redundancy_risk(hi), Q.redundancy_risk(lo))
        self.assertGreater(Q.short_convexity(hi), Q.short_convexity(lo))

    def test_base_rates_from_file(self):
        br = Q.base_rates()
        self.assertEqual(br["n"], 9)
        self.assertGreater(br["median_equity_unwind_pct"], 50)

    def test_regime_short_watch_on_trigger(self):
        node = {"id": "x", "label": "X", "status": "binding", "prevalence": 0.9,
                "crowdedness": 0.9, "kill_signals": ["k1", "k2", "k3", "k4"], "tickers": []}
        self.assertEqual(Q.regime(node, {}, [])["regime"], "DISSOLUTION_WATCH")
        self.assertEqual(Q.regime(node, {}, ["k1"])["regime"], "SHORT_WATCH")
        self.assertEqual(Q.regime(node, {}, ["k1", "k2", "k3", "k4"])["regime"], "EXIT")

    def test_missing_readings_neutral(self):
        node = {"prevalence": 0.8}
        full = Q.binding_score(node, {"spot_vs_peak": 1.0, "book_to_bill": 1.5})
        empty = Q.binding_score(node, {})
        self.assertGreater(full["binding"], empty["binding"])
        self.assertAlmostEqual(empty["from_readings"], 0.5)


class TestRender(unittest.TestCase):
    def test_render_never_raises_minimal(self):
        g = {"name": "t", "thesis": "t", "nodes": [{"id": "a", "label": "A"}]}
        out = G.render(g, {}, {})
        self.assertIn("A", out)

    def test_destroy_constrain_lines(self):
        n = {"destroy_paths": ["X dies"], "constrain_paths": ["Y blocks"]}
        lines = G.destroy_constrain(n)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("DESTROY"))


if __name__ == "__main__":
    unittest.main()
