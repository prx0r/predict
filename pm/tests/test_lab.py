"""bneck2 lab tests — preregister/receipt/report honesty properties."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import lab as LAB


class TestLab(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self._r, self._h = LAB.RECEIPTS, LAB.HYPS
        self._p = LAB.PREDICTIONS
        LAB.RECEIPTS = self.tmp / "receipts.jsonl"
        LAB.HYPS = self.tmp / "hypotheses"
        LAB.PREDICTIONS = self.tmp / "predictions.jsonl"

    def tearDown(self):
        LAB.RECEIPTS, LAB.HYPS = self._r, self._h
        LAB.PREDICTIONS = self._p
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
    def test_pilot_flag(self):
        r = LAB.receipt("TEST-H", {"x": 1}, "CONFIRMED", 3,
                        ts="2026-09-10T00:00:00Z")
        self.assertTrue(r["directional_only"])
        self.assertEqual(len(r["inputs_hash"]), 16)

    def test_no_pilot_flag_at_30(self):
        r = LAB.receipt("TEST-H", {"x": 1}, "REFUTED", 30,
                        ts="2026-09-10T00:00:00Z")
        self.assertFalse(r["directional_only"])

    def test_bad_verdict_rejected(self):
        with self.assertRaises(AssertionError):
            LAB.receipt("TEST-H", {}, "MAYBE", 5)

    def test_wilson_bounds(self):
        from bneck2 import lab as LAB
        w = LAB.wilson(2, 3)
        self.assertLess(w["lo"], 0.67)
        self.assertGreater(w["hi"], 0.67)
        self.assertEqual(LAB.wilson(0, 0)["hi"], 1.0)

    def test_support_and_ledger(self):
        from bneck2 import lab as LAB
        LAB.receipt("H-A", {"x": 1}, "CONFIRMED", 40, ts="2026-09-10T00:00:00Z")
        LAB.receipt("H-B", {"x": 1}, "REFUTED", 40, ts="2026-09-10T00:00:00Z")
        LAB.receipt("H-C", {"x": 1}, "INCONCLUSIVE", 2, ts="2026-09-10T00:00:00Z")
        s = LAB.support_rate()
        self.assertEqual((s["decided"], s["open"]), (2, 1))
        leg = LAB.possibility_ledger()
        self.assertEqual((leg["confirmed"], leg["refuted"], leg["open"]), (1, 1, 1))

    def test_threads_counter_shape(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "threads", str(ROOT / "scripts" / "threads.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        got = mod.counts()
        self.assertIn("unknowns_open", got)
        self.assertGreaterEqual(got["hyps_open"], 0)

    def test_predictions_resolve(self):
        from bneck2 import lab as LAB
        LAB.predict("v", "t", +1, "2026-01-01", note="past")
        LAB.predict("v", "t", -1, "2027-01-01", note="future")
        done = LAB.resolve_due(lambda r: +1)
        self.assertEqual(len(done), 1)
        self.assertTrue(done[0]["hit"])
        self.assertEqual(
            sum(1 for r in LAB.load_predictions() if r.get("resolved") is None), 1)

    def test_coverage_shape(self):
        from bneck2 import lab as LAB
        cov = LAB.verdict_coverage()
        self.assertIn("cells_tested", cov)
        self.assertGreaterEqual(cov["rows"], 400)

    def test_report_rebuilds(self):
        LAB.receipt("TEST-H", {"x": 1}, "CONFIRMED", 3,
                    ts="2026-09-10T00:00:00Z")
        rep = LAB.report()
        self.assertIn("TEST-H", rep)


if __name__ == "__main__":
    unittest.main()
