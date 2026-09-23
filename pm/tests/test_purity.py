"""Purity boundary tests (peer-review P0 fix).

evaluate(), pm_reading(), sec_burst(), attack_intensity() must perform
NO network I/O and import NO collector modules. We enforce it two ways:
1. AST: those functions contain no Import/ImportFrom nodes and no
   references to urllib/socket/http collectors.
2. Live explosion: socket.socket and urlopen raise if touched while
   evaluating fixtures.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def _fn_nodes():
    tree = ast.parse((ROOT / "bneck2" / "killfeed.py").read_text(encoding="utf-8"))
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


class TestNoImportsInEval(unittest.TestCase):
    def test_no_import_statements(self):
        fns = _fn_nodes()
        for name in ("pm_reading", "evaluate", "sec_burst", "attack_intensity"):
            for node in ast.walk(fns[name]):
                self.assertNotIsInstance(
                    node, (ast.Import, ast.ImportFrom),
                    f"{name} contains an import statement")

    def test_no_network_names(self):
        fns = _fn_nodes()
        for name in ("pm_reading", "evaluate", "sec_burst",
                     "attack_intensity"):
            names = set()
            for node in ast.walk(fns[name]):
                if isinstance(node, ast.Name):
                    names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    continue  # docstrings/prose may name things; code may not
            for banned in ("urlopen", "Request", "socket", "collectors",
                           "urllib", "httpx", "requests", "snapshot_all",
                           "consensus", "fetch_markets", "fetch_yearly",
                           "fetch_recent_filings"):
                self.assertNotIn(banned, names,
                                 f"{name} references network: {banned}")


class TestSocketsExplode(unittest.TestCase):
    def test_evaluate_with_dead_network(self):
        import socket
        import urllib.request
        from bneck2 import killfeed as K
        real_socket, real_urlopen = socket.socket, urllib.request.urlopen

        def boom(*a, **k):
            raise AssertionError("network touched during evaluation")

        socket.socket = boom
        urllib.request.urlopen = boom
        try:
            snaps = [{"question": "q?", "p": 0.7, "volume": 5_000_000.0,
                      "liquidity": 300_000.0, "tier": "high-liquidity",
                      "venue": "polymarket", "conditionId": "0xabc",
                      "depth_top5": 2_000_000.0, "spread": 0.05,
                      "ts": "t", "source_hash": "x"}]
            rows = K.evaluate({"id": "n"}, sec=[{"form": "4", "accession": "a1"}],
                              velocity={"total_works": 10, "per_year": {2021: 1, 2022: 2}},
                              markets=snaps, ts="t",
                              whales=[{"total_usd": 60000.0, "n_wallets": 4,
                                       "outcome": 1, "question": "q?"}])
            kinds = [r["signal"] for r in rows]
            self.assertIn("sec-burst(Form4>=5,deal>=2)", kinds)
            self.assertIn("pm-clock", kinds)
            pm = next(r for r in rows if r["signal"] == "pm-clock")
            self.assertTrue(pm["measured"].startswith(
                "p=0.7 high-liquidity polymarket depth=$2,000,000 "
                "spread=0.05 rel=0.92"))
            self.assertTrue(any("_extra_signals" in r for r in rows))
        finally:
            socket.socket = real_socket
            urllib.request.urlopen = real_urlopen


class TestTypedLinks(unittest.TestCase):
    def test_unlinked_is_discovery(self):
        from bneck2 import killfeed as K
        snaps = [{"question": "Will it rain on Mars?", "p": 0.9,
                  "volume": 1e6, "liquidity": 1e5, "tier": "mid-liquidity",
                  "venue": "polymarket"}]
        r = K.pm_reading(snaps, links=[])
        self.assertEqual(r["evidence_grade"], "discovery")
        self.assertIsNone(r["link"])

    def test_linked_carries_polarity(self):
        from bneck2 import killfeed as K
        links = K._pm_links()
        self.assertTrue(links)
        snaps = [{"question": "OpenAI announces AGI before 2027?", "p": 0.23,
                  "volume": 1e6, "liquidity": 1e5, "tier": "mid-liquidity",
                  "venue": "polymarket"}]
        r = K.pm_reading(snaps, links)
        self.assertEqual(r["evidence_grade"], "linked")
        self.assertEqual(r["link"]["polarity"], "+")


class TestAccessionLedger(unittest.TestCase):
    def test_split_unseen_idempotent(self):
        from bneck2 import killfeed as K
        filings = [{"form": "4", "accession": "a1"},
                   {"form": "8-K", "accession": "a2"},
                   {"form": "4", "accession": ""}]
        new1, seen = K.split_unseen("C1", filings, {})
        self.assertEqual(len(new1), 2)
        new2, seen2 = K.split_unseen("C1", filings, seen)
        self.assertEqual(new2, [])
        self.assertEqual(sorted(seen2["C1"]), ["a1", "a2"])

    def test_empty_accession_never_counted(self):
        from bneck2 import killfeed as K
        new1, _ = K.split_unseen("C1", [{"form": "4", "accession": ""}], {})
        self.assertEqual(new1, [])


if __name__ == "__main__":
    unittest.main()
