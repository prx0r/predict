"""bneck2 v2-module tests — stdlib unittest, no network (fixtures only)."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import labs as L
from bneck2 import diggers as D
from bneck2 import patents as P
from bneck2 import ceo as C
from collectors import sec, github, openalex, polymarket, usaspending, grants


class TestLabSignal(unittest.TestCase):
    def test_nuclear_beats_tweet(self):
        tweet = {"kind": "tweet", "amount_usd": None, "specificity": 0.2,
                 "relevance": 0.3, "duration_years": 0.1}
        nuke = {"kind": "multidecade-contract", "amount_usd": 15e9,
                "specificity": 0.9, "relevance": 1.0, "duration_years": 22}
        self.assertGreater(L.lab_signal(nuke)["score"], L.lab_signal(tweet)["score"] * 100)

    def test_formula_shape(self):
        e = {"kind": "acquisition", "amount_usd": 1e9, "specificity": 1.0,
             "relevance": 1.0, "duration_years": 25}
        expect = math.log1p(1e9) * 0.5 * 1.0 * 1.0 * 1.0
        self.assertAlmostEqual(L.lab_signal(e)["score"], round(expect, 3))

    def test_unpriced_flagged(self):
        s = L.lab_signal({"kind": "deployment", "specificity": 0.8,
                          "relevance": 0.9, "duration_years": 5})
        self.assertTrue(s["estimated_amount"])

    def test_diversification_threshold(self):
        many = [{"lab": "OpenAI", "target": t} for t in
                ["Cerebras X", "AWS Trainium", "AMD chips", "Broadcom Y", "NVIDIA Z"]]
        self.assertIn("no single", L.diversification_reading(many))
        few = [{"lab": "OpenAI", "target": "NVIDIA Z"}]
        self.assertIn("below", L.diversification_reading(few))

    def test_seed_commitments_rank(self):
        ranked = L.rank_commitments(L.load_commitments())
        self.assertGreater(len(ranked), 5)
        self.assertEqual(ranked[0]["target"], "Finland AI infra + 22-year nuclear agreement")


class TestDiggers(unittest.TestCase):
    def test_no_evidence_no_advance(self):
        d = {"rung": "CLAIM", "evidence": []}
        with self.assertRaises(ValueError):
            D.advance(dict(d), "SILICON", "")

    def test_stepwise_only(self):
        d = {"rung": "CLAIM", "evidence": []}
        D.advance(d, "SILICON", "http://x")
        self.assertEqual(d["rung"], "SILICON")
        D.advance(d, "NORMALIZED", "http://x")  # skip refused
        self.assertEqual(d["rung"], "SILICON")

    def test_cn101_not_substitution_ready(self):
        dig = [d for d in D.load_diggers() if d["name"] == "Normal Computing CN101"][0]
        self.assertEqual(dig["rung"], "PEER_REVIEW")
        self.assertFalse(D.substitution_ready(dig))

    def test_rung_order(self):
        self.assertLess(D.rung_index("CLAIM"), D.rung_index("DEPLOYED"))


class TestPatents(unittest.TestCase):
    def test_full_bypass_not_chokepoint(self):
        m = P.new_map()
        for t in ["a", "b"]:
            P.require(m, "cap", t)
            P.cover(m, t, "fam", "Zed")
            P.substitute(m, t, "alt")
        m["architectures"] = {"arch1": ["a", "b"]}
        self.assertEqual(P.legal_chokepoint(m, "Zed")["share"], 0.0)

    def test_trapped_arch_is_chokepoint(self):
        m = P.new_map()
        P.require(m, "cap", "x")
        P.cover(m, "x", "fam1", "Zed")
        m["architectures"] = {"arch1": ["x"]}
        self.assertEqual(P.legal_chokepoint(m, "Zed")["share"], 1.0)

    def test_ionq_partial(self):
        m = P.load_map()
        r = P.legal_chokepoint(m, "IonQ")
        self.assertGreater(r["architectures"], 0)
        self.assertLess(r["share"], 1.0)


class TestCeo(unittest.TestCase):
    def test_known_vs_unknown(self):
        d = C.load_ledger()
        self.assertGreaterEqual(len(d["known"]), 2)
        persons = {u["person"] for u in d["unknown"]}
        self.assertIn("Sam Altman", persons)

    def test_no_duplicate_gaps(self):
        d = {"known": [], "unknown": []}
        C.flag_unknown(d, "X", "holdings", "why")
        C.flag_unknown(d, "X", "holdings", "why")
        self.assertEqual(len(d["unknown"]), 1)


class TestCollectors(unittest.TestCase):
    def test_sec_url_and_parse(self):
        self.assertIn("CIK0001318605", sec.submissions_url("1318605"))
        doc = {"filings": {"recent": {"form": ["4", "10-K", "8-K"],
               "filingDate": ["2026-01-01"] * 3, "accessionNumber": ["a"] * 3,
               "primaryDocument": ["d"] * 3}}}
        rows = sec.parse_recent_filings(doc)
        self.assertEqual([r["form"] for r in rows], ["4", "8-K"])

    def test_github_keyword_parse(self):
        ev = [{"type": "PushEvent", "repo": {"name": "o/r"}, "actor": {"login": "u"},
               "created_at": "t", "payload": {"ref": "kv-cache-opt",
                "commits": [{"message": "speed up attention"}]}}]
        rows = github.parse_implementation_signals(ev)
        self.assertEqual(len(rows), 1)
        self.assertIn("kv", rows[0]["keyword_hits"])

    def test_openalex_velocity(self):
        doc = {"meta": {"count": 5}, "results": [
            {"publication_year": 2025, "authorships": [{"author": {"display_name": "A"}}]},
            {"publication_year": 2026, "authorships": [{"author": {"display_name": "A"}}]}]}
        v = openalex.parse_velocity(doc)
        self.assertEqual(v["per_year"], {2025: 1, 2026: 1})
        self.assertEqual(v["top_authors"][0][0], "A")

    def test_polymarket_tiers(self):
        self.assertEqual(polymarket.liquidity_tier(3e6, 0), "high-liquidity")
        self.assertEqual(polymarket.liquidity_tier(0, 0), "low-liquidity")
        doc = [{"title": "Q?", "markets": [{"question": "Q?", "outcomePrices": "[\"0.57\",\"0.43\"]",
                "volume": "100", "liquidity": "50"}]}]
        rows = polymarket.parse_markets(doc)
        self.assertAlmostEqual(rows[0]["p"], 0.57)

    def test_usaspending_grants_parse(self):
        doc = {"results": [{"Award ID": "1", "Recipient Name": "Lab",
                "Award Amount": 5e8, "Awarding Agency": "DOE",
                "Award Type": "Grant", "Start Date": "2026-01-01"}]}
        self.assertEqual(usaspending.parse_awards(doc)[0]["recipient"], "Lab")
        gdoc = {"data": {"oppHits": [{"id": "i", "title": "Photonic packaging",
                "agencyName": "DOE", "oppStatus": "posted",
                "openDate": "2026-01-01", "closeDate": "2026-06-01"}]}}
        self.assertEqual(grants.parse_opps(gdoc)[0]["agency"], "DOE")


if __name__ == "__main__":
    unittest.main()
