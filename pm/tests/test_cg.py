"""cg-structure tests: sealed eval, rebuild determinism, run files, cache."""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVAL_SIDE = ["bneck2/backtest.py", "bneck2/evidence.py", "bneck2/updater.py",
             "bneck2/quant.py", "bneck2/worlds.py"]
FORBIDDEN = ("experiments", "killfeed", "scripts.")


class TestSealedEval(unittest.TestCase):
    def test_eval_side_imports_nothing_live(self):
        for rel in EVAL_SIDE:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            mods = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods.add(node.module.split(".")[0])
            for f in FORBIDDEN:
                self.assertNotIn(f.rstrip("."), mods, f"{rel} imports {f}")

    def test_experiments_never_write_panel(self):
        txt = (ROOT / "bneck2" / "experiments.py").read_text(encoding="utf-8")
        self.assertNotIn("panel.jsonl", txt)


class TestRebuild(unittest.TestCase):
    def test_report_deterministic(self):
        from bneck2 import lab as LAB
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "r.jsonl"
        old = LAB.RECEIPTS
        LAB.RECEIPTS = tmp
        try:
            LAB.receipt("H", {"x": 1}, "CONFIRMED", 40, ts="2026-01-01T00:00:00Z")
            self.assertEqual(LAB.report(), LAB.report())
        finally:
            LAB.RECEIPTS = old

    def test_run_file_content_addressed(self):
        from bneck2 import lab as LAB
        import tempfile
        old = LAB.RUNS
        LAB.RUNS = Path(tempfile.mkdtemp())
        try:
            a = LAB.run_file("H", {"x": 1}, {"y": 2}, ts="2026-01-01T00:00:00Z")
            b = LAB.run_file("H", {"x": 1}, {"y": 2}, ts="2026-01-01T00:00:00Z")
            self.assertEqual(a, b)
            self.assertTrue(a.exists())
        finally:
            LAB.RUNS = old

    def test_cache_roundtrip(self):
        from bneck2 import lab as LAB
        self.assertIsNone(LAB.cache_get("test-nonexistent-key-zzz"))
        self.assertEqual(LAB.cache_key("a", "b"), LAB.cache_key("a", "b"))
        self.assertNotEqual(LAB.cache_key("a", "b"), LAB.cache_key("a", "c"))


class TestExperienceBuild(unittest.TestCase):
    def test_build_counts(self):
        import tempfile
        from pathlib import Path as P
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "experience_build", str(ROOT / "scripts" / "experience_build.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = mod.build(P(tempfile.mkdtemp()) / "exp.db")
        self.assertGreater(out["receipts"], 0)
        self.assertGreater(out["verdicts"], 0)
        self.assertIn("sha", out)


class TestMCPHeadless(unittest.TestCase):
    def test_full_mcp_battery(self):
        import subprocess
        import sys as _sys
        receipts = ROOT / "experimentation" / "receipts.jsonl"
        runs = ROOT / "experimentation" / "runs"
        before = receipts.read_bytes() if receipts.exists() else b""
        before_runs = set(p.name for p in runs.glob("*.json")) if runs.exists() else set()
        try:
            r = subprocess.run(
                [_sys.executable, str(ROOT / "scripts" / "mcp_test.py")],
                capture_output=True, text=True, timeout=600, cwd=str(ROOT))
            self.assertEqual(r.returncode, 0,
                             f"mcp battery failed:\n{r.stdout[-1500:]}\n{r.stderr[-500:]}")
        finally:
            receipts.write_bytes(before)
            if runs.exists():
                for p in runs.glob("*.json"):
                    if p.name not in before_runs:
                        p.unlink()


if __name__ == "__main__":
    unittest.main()
