"""bneck belief-machine tests — stdlib unittest, no network.

Run: /usr/bin/python3 -m unittest discover -s tests -v
Covers msg-18 mechanics: lineage, disagreement, Bayesian update trail,
Jevons trap, forecaster skill, empirical calibration.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import belief as B
from bneck2 import calibration as C
from bneck2 import forecasters as F
from bneck2 import jevons as J
from bneck2 import updater as U


def claim(i, p, clock="expert", origin=None, derived=None):
    return B.new_claim(f"c{i}", "e1", f"text {i}", p, clock,
                       origin_claim_id=origin or f"c{i}",
                       derived_from=derived or [])


class TestLineage(unittest.TestCase):
    def test_six_echoes_count_once(self):
        root = claim(0, 0.7)
        echoes = [claim(i, 0.7 + i * 0.01, origin="c0", derived=["c0"]) for i in range(1, 7)]
        out = B.combine([root] + echoes)
        self.assertEqual(out["n"], 7)
        self.assertEqual(out["n_independent"], 1)
        self.assertAlmostEqual(out["p"], sum(c["p"] for c in [root] + echoes) / 7, places=3)

    def test_independent_convergence_counts(self):
        a = claim(0, 0.8)
        b = claim(1, 0.6)
        out = B.combine([a, b])
        self.assertEqual(out["n_independent"], 2)
        self.assertAlmostEqual(out["p"], 0.7)


class TestDisagreement(unittest.TestCase):
    def test_consensus_gap(self):
        split = {"hard": {"p": 0.78, "n": 2, "n_independent": 2},
                 "expert": {"p": 0.72, "n": 2, "n_independent": 2},
                 "pm": {"p": 0.57, "n": 1, "n_independent": 1},
                 "equity": {"p": 0.18, "n": 1, "n_independent": 1}}
        d = B.disagreement(split)
        self.assertTrue(any("CONSENSUS_GAP" in f for f in d["flags"]))
        self.assertAlmostEqual(d["gap_hard_equity"], 0.6)

    def test_crowded_narrative(self):
        split = {"hard": {"p": 0.22, "n": 1, "n_independent": 1},
                 "expert": {"p": 0.95, "n": 5, "n_independent": 1},
                 "pm": {"p": 0.84, "n": 1, "n_independent": 1},
                 "equity": {"p": 0.90, "n": 1, "n_independent": 1}}
        d = B.disagreement(split)
        self.assertTrue(any("CROWDED_NARRATIVE" in f for f in d["flags"]))


class TestUpdater(unittest.TestCase):
    def test_fuse_moves_toward_evidence(self):
        out = U.fuse(0.5, [(0.9, 2.0)])
        self.assertGreater(out["posterior"], 0.7)
        back = U.fuse(0.9, [(0.1, 2.0)])
        self.assertLess(back["posterior"], 0.5)

    def test_hbm_walk(self):
        """Msg-18 walk: .11 -> .24 -> .31 -> .42 -> .54 -> .89 must land high."""
        p = 0.11
        for signal in (0.24, 0.31, 0.42, 0.54, 0.89):
            p = U.fuse(p, [(signal, 1.0)])["posterior"]
        self.assertGreater(p, 0.6)

    def test_trigger_on_crossing(self):
        g = {"edges": [{"source": "a", "target": "b", "confidence": 0.92}]}
        g2, ev = U.update_edge(g, ("a", "b"), 0.29, cause="benchmark")
        self.assertTrue(ev["trigger"])
        self.assertEqual(g2["edges"][0]["confidence"], 0.29)
        self.assertIn("valid_from", g2["edges"][0])

    def test_no_trigger_without_crossing(self):
        g = {"edges": [{"source": "a", "target": "b", "confidence": 0.92}]}
        _, ev = U.update_edge(g, ("a", "b"), 0.71, cause="rumor")
        self.assertFalse(ev["trigger"])

    def test_downstream_tickers(self):
        g = {"nodes": [{"id": "a", "label": "A", "tickers": ["MU"]},
                       {"id": "b", "label": "B", "tickers": ["NVDA"]}],
             "edges": [{"source": "a", "target": "b"}]}
        d = U.downstream_tickers(g, ("a", "b"))
        self.assertEqual(d["tickers"], ["MU", "NVDA"])


class TestJevons(unittest.TestCase):
    def test_expansion_trap(self):
        out = J.classify(0.8, 20.0)  # msg-18 example: 0.2*20 = 4.0
        self.assertEqual(out["verdict"], "EXPANSION")
        self.assertAlmostEqual(out["residual_demand"], 4.0)

    def test_true_substitution(self):
        out = J.classify(0.9, 5.0)
        self.assertEqual(out["verdict"], "SUBSTITUTION")
        self.assertTrue(J.check_kill({"id": "m"}, 0.9, 5.0)["allowed"])
        self.assertFalse(J.check_kill({"id": "m"}, 0.8, 20.0)["allowed"])


class TestForecasters(unittest.TestCase):
    def test_unknown_is_prior(self):
        self.assertEqual(F.weight(F.new_book(), "nobody", "chips"), 0.5)

    def test_good_record_raises(self):
        b = F.new_book()
        for _ in range(3):
            F.record(b, "moody", "photonics", 0.8, True, lead_days=19,
                     specific=True, novel=True, independent=True)
        s = F.skill(b, "moody", "photonics")
        self.assertGreater(s["skill"], 0.6)
        self.assertEqual(s["n"], 3)

    def test_bad_record_drops(self):
        b = F.new_book()
        for _ in range(3):
            F.record(b, "hype", "chips", 0.9, False, lead_days=0)
        self.assertLess(F.skill(b, "hype", "chips")["skill"], 0.5)

    def test_domain_separation(self):
        b = F.new_book()
        F.record(b, "q", "quantum", 0.9, True, lead_days=30)
        self.assertNotEqual(F.skill(b, "q", "quantum")["skill"],
                            F.skill(b, "q", "chips")["skill"])


class TestCalibration(unittest.TestCase):
    def test_prior_flagged(self):
        r = C.reliability(C.new_table(), "polymarket", "high-liquidity")
        self.assertTrue(r["prior"])
        self.assertEqual(r["n"], 0)

    def test_weights_emerge(self):
        t = C.new_table()
        for _ in range(4):
            C.record(t, "github", "release", True)
        C.record(t, "github", "release", False)
        r = C.reliability(t, "github", "release")
        self.assertFalse(r["prior"])
        self.assertAlmostEqual(r["p"], (4 + 1) / (5 + 2), places=3)


if __name__ == "__main__":
    unittest.main()
