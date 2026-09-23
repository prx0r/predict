"""bneck2 import tests — pack merge + kernel bridge (stdlib, offline)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import kernel_bridge as KB
from bneck2 import labs as L
from bneck2 import diggers as D


class TestPackMerge(unittest.TestCase):
    def test_commitments_grew(self):
        commits = L.load_commitments()
        self.assertGreaterEqual(len(commits), 25)
        labs = {c["lab"] for c in commits}
        self.assertTrue({"OpenAI", "Google", "Anthropic"} <= labs)

    def test_lab_signal_still_ranks_nuclear_top(self):
        ranked = L.rank_commitments(L.load_commitments())
        self.assertIn("nuclear", ranked[0]["target"].lower())

    def test_diggers_grew_with_bars(self):
        ds = D.load_diggers()
        self.assertGreaterEqual(len(ds), 10)
        names = [d["name"] for d in ds]
        self.assertTrue(any("Cerebras" in n or "Groq" in n or "Etched" in n for n in names))

    def test_import_idempotent(self):
        import scripts.import_pack as IP
        from bneck2 import labs as LL
        n0 = len(LL.load_commitments())
        d0 = len(D.load_diggers())
        IP.import_events()
        IP.import_diggers()
        self.assertEqual(len(LL.load_commitments()), n0)
        self.assertEqual(len(D.load_diggers()), d0)


class TestBridge(unittest.TestCase):
    def test_reports_missing_deps(self):
        d = KB.describe()
        self.assertIn("native_equivalents", d)
        self.assertIsInstance(d["kernel_available"], bool)

    def test_demo_panel_loads(self):
        rows = KB.demo_companies()
        self.assertGreater(len(rows), 0)
        self.assertIn("ticker", rows[0])
        self.assertIn("technological_duration", rows[0])
        panel = KB.demo_panel()
        self.assertGreater(len(panel), 0)
        self.assertIn("forward_return", panel[0])


if __name__ == "__main__":
    unittest.main()
