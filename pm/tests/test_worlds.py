"""bneck2 worlds tests — stdlib unittest, no network."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import worlds as W
from bneck2 import updater as U


class TestWorldsSeed(unittest.TestCase):
    def test_probs_sum_to_one(self):
        doc = W.load_worlds()
        self.assertAlmostEqual(sum(w["p_you"] for w in doc["worlds"]), 1.0)
        self.assertAlmostEqual(sum(w["p_market"] for w in doc["worlds"]), 1.0)

    def test_gaps_direction(self):
        gaps = {g["id"]: g["gap"] for g in W.world_gaps(W.load_worlds()["worlds"])}
        self.assertGreater(gaps["agent-openai"], 0)   # we overweight vs market
        self.assertLess(gaps["slowdown"], 0)          # market overweight slowdown


class TestObsolescence(unittest.TestCase):
    def test_workflow_flags_arbitrage(self):
        doc = W.load_worlds()
        inc = next(i for i in doc["incumbents"] if i["id"] == "legacy-workflow-sw")
        out = W.signal_company(inc, doc["worlds"])
        self.assertEqual(out["verdict"], "OBSOLESCENCE_ARBITRAGE")
        self.assertLess(out["signal_usd"], 0)  # pool shrinks in our distribution
        self.assertAlmostEqual(out["impaired_share"], 0.9)
        self.assertAlmostEqual(out["gap"], 0.7)

    def test_therapy_pool_quiet_without_cure_world(self):
        doc = W.load_worlds()
        inc = next(i for i in doc["incumbents"] if i["id"] == "therapy-paradigm-rx")
        out = W.signal_company(inc, doc["worlds"])
        self.assertEqual(out["verdict"], "NONE")
        self.assertEqual(out["signal_usd"], 0)

    def test_screen_sorts_worst_first(self):
        rows = W.screen()
        self.assertLessEqual(rows[0]["signal_usd"], rows[-1]["signal_usd"])


class TestMilestoneWiring(unittest.TestCase):
    def test_milestone_prefix_and_stamp(self):
        g = {"edges": [{"source": "a", "target": "b", "confidence": 0.92}]}
        g2, ev = U.milestone_event(g, ("a", "b"), 0.29, "NS-2026",
                                   "10k agents, 88h, Lean formalization")
        self.assertTrue(ev["cause"].startswith("MILESTONE"))
        self.assertTrue(ev["trigger"])
        self.assertEqual(g2["edges"][0]["confidence"], 0.29)


if __name__ == "__main__":
    unittest.main()
