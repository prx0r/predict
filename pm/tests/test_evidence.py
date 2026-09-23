"""bneck evidence + criticality + priors tests — stdlib unittest, no network."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import evidence as E
from bneck2 import forecasters as F
from bneck2 import graph as G


class TestKillObservations(unittest.TestCase):
    def test_verdict_gate(self):
        with self.assertRaises(AssertionError):
            E.log_kill_observation("x", "s", "m", "t", "MAYBE")

    def test_log_and_read_roundtrip_tmp(self):
        import bneck2.evidence as EV
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k.jsonl"
            orig = EV.KILL_OBS
            EV.KILL_OBS = p
            try:
                EV.log_kill_observation("memory_hbm", "HBM spot -8%", "-8%",
                                        "first kill at -15%", "NOT TRIGGERED", "trendforce")
                rows = EV.read_kill_observations("memory_hbm")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["verdict"], "NOT TRIGGERED")
            finally:
                EV.KILL_OBS = orig


class TestUnknowns(unittest.TestCase):
    def test_add_close_tmp(self):
        import bneck2.evidence as EV
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "u.json"
            orig = EV.UNKNOWNS
            EV.UNKNOWNS = p
            try:
                row = EV.add_unknown("Hynix customer split", "HBM share by buyer",
                                     "Hynix 10-K, earnings", "HBM demand model")
                self.assertEqual(row["status"], "open")
                self.assertTrue(EV.close_unknown(row["id"], "found in Q2 deck"))
                self.assertEqual(EV.read_unknowns(), [])
                self.assertEqual(len(EV.read_unknowns(open_only=False)), 1)
            finally:
                EV.UNKNOWNS = orig


class TestSignals(unittest.TestCase):
    def test_direction_gate(self):
        with self.assertRaises(AssertionError):
            E.log_signal("MU", "spot", 2, 0.5, 0.5)

    def test_ticker_upper_tmp(self):
        import bneck2.evidence as EV
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            orig = EV.SIGNALS
            EV.SIGNALS = p
            try:
                EV.log_signal("mu", "inventory", -1, 0.7, 0.8, "edgar")
                self.assertEqual(EV.read_signals("MU")[0]["ticker"], "MU")
            finally:
                EV.SIGNALS = orig


class TestCriticality(unittest.TestCase):
    def test_hub_outranks_leaf(self):
        g = {"nodes": [{"id": "a", "label": "A", "tickers": ["X"]},
                       {"id": "b", "label": "B", "tickers": ["Y"]},
                       {"id": "c", "label": "C"}],
             "edges": [{"source": "a", "target": "b"},
                       {"source": "c", "target": "b"}]}
        c = G.criticality(g)
        self.assertGreater(c["b"], c["a"])
        self.assertGreater(c["b"], 0)
        self.assertEqual(c["a"], 0.0)

    def test_live_graph_top_is_constraint(self):
        g = G.load_graph()
        c = G.criticality(g)
        top = max(c.items(), key=lambda kv: kv[1])[0]
        self.assertIn(top, {n["id"] for n in g["nodes"]})
        self.assertGreater(c[top], 0)


class TestPriors(unittest.TestCase):
    def test_forecaster_watchlist_exists(self):
        p = ROOT / "data" / "beliefs" / "forecasters.json"
        book = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("MoodyWriter13", book["handles"])
        for h, rec in book["handles"].items():
            for t in rec.get("topics", {}).values():
                self.assertEqual(t.get("n", 0), 0)

    def test_watchlist_all_prior(self):
        book = json.loads((ROOT / "data" / "beliefs" / "forecasters.json").read_text(encoding="utf-8"))
        for h in book["handles"]:
            self.assertEqual(F.weight(book, h, "anything"), 0.5)


if __name__ == "__main__":
    unittest.main()
