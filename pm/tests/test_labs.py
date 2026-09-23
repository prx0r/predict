"""bneck labs tests — stdlib unittest, no network."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import labs


class TestLabs(unittest.TestCase):
    def test_seed_loads(self):
        deals = labs.load_deals()
        self.assertGreaterEqual(len(deals), 10)
        for d in deals:
            for f in ("lab", "target", "kind", "tag", "date"):
                self.assertIn(f, d)

    def test_attention_counts(self):
        deals = labs.load_deals()
        att = labs.attention_by_tag(deals)
        self.assertGreater(att["by_count"].get("agent-infra", 0), 3)
        self.assertIn("deployment-labor", att["by_count"])

    def test_substrate_gap_is_zero(self):
        sub = labs.substrate_share(labs.load_deals())
        self.assertEqual(sub["substrate_deals"], 0)
        self.assertGreater(sub["total_deals"], 0)

    def test_gap_report_names_trigger(self):
        rep = labs.gap_report(labs.load_deals())
        self.assertIn("thermodynamic", rep)
        self.assertIn("Nvidia-coverage", rep)

    def test_empty_safe(self):
        self.assertEqual(labs.substrate_share([])["share"], 0.0)
        self.assertIn("Tracked deals: 0", labs.gap_report([]))


if __name__ == "__main__":
    unittest.main()
