"""bneck2 wiring tests — scarcity, killfeed, seed_claims, backtest/implied/
obsolescence ports. All offline (fixtures only, no network)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import scarcity as S
from bneck2 import killfeed as K
from bneck2 import backtest as BT
from bneck2 import implied as IM
from bneck2 import obsolescence as OB


class TestScarcity(unittest.TestCase):
    def test_ported_map_present(self):
        self.assertGreaterEqual(len(S.PORTED_MAP), 10)

    def test_scan_finds_node_and_tickers(self):
        rows = S.build_map()
        hits = S.scan_text("automated cryogenic wafer probing at 4 kelvin for HBM yield", rows)
        self.assertTrue(hits)
        self.assertIn("FORM", S.implied_tickers("cryogenic wafer probing yield", rows))

    def test_empty_text_no_hits(self):
        self.assertEqual(S.scan_text("  ", S.build_map()), [])

    def test_every_node_has_keywords(self):
        for r in S.build_map():
            if r["source"] == "graph_v2":
                self.assertTrue(r["keywords"], r["node_id"])


class TestKillfeed(unittest.TestCase):
    NODE = {"id": "memory_hbm", "label": "HBM / high-bandwidth memory",
            "tickers": ["MU"], "kill_signals": ["HBM price declines"]}

    def test_attack_intensity_high(self):
        vel = {"total_works": 500,
               "per_year": {2021: 40, 2022: 50, 2023: 120, 2024: 140}}
        a = K.attack_intensity(vel)
        self.assertEqual(a["tier"], "HIGH")
        self.assertGreater(a["growth"], 1.0)

    def test_attack_intensity_thin_literature_not_high(self):
        vel = {"total_works": 12,
               "per_year": {2021: 1, 2022: 1, 2023: 5, 2024: 5}}
        self.assertEqual(K.attack_intensity(vel)["tier"], "normal")

    def test_velocity_fetch_failed_inconclusive(self):
        rows = K.evaluate(self.NODE,
                          velocity={"ok": False, "total_works": 0,
                                    "per_year": {}},
                          markets=[], ts="t")
        by_src = {r["source"]: r["verdict"] for r in rows}
        self.assertEqual(by_src["openalex"], "INCONCLUSIVE")
        # pm leg still evaluated (no early return)
        self.assertEqual(by_src["polymarket"], "INCONCLUSIVE")

    def test_yearly_parser(self):
        from collectors import openalex as OA
        doc = {"group_by": [{"key": "2024", "count": 100},
                            {"key": "2025", "count": 150}]}
        out = OA.parse_yearly(doc)
        self.assertEqual(out["per_year"], {2024: 100, 2025: 150})
        self.assertEqual(out["total_works"], 250)

    def test_sec_burst_fires(self):
        filings = [{"form": "4"}] * 5 + [{"form": "8-K"}]
        rows = K.evaluate(self.NODE, sec=filings, ts="t")
        self.assertEqual(rows[0]["verdict"], "TRIGGERED")

    def test_sec_quiet_no_trigger(self):
        rows = K.evaluate(self.NODE, sec=[{"form": "4"}], ts="t")
        self.assertEqual(rows[0]["verdict"], "NOT TRIGGERED")

    def test_pm_empty_inconclusive(self):
        rows = K.evaluate(self.NODE, markets=[], ts="t")
        self.assertEqual(rows[0]["verdict"], "INCONCLUSIVE")

    def test_pm_best_book_reliability(self):
        mkts = [{"question": "q?", "p": 0.7, "volume": 5_000_000,
                 "liquidity": 300_000, "tier": "high-liquidity"}]
        rows = K.evaluate(self.NODE, markets=mkts, ts="t")
        self.assertIn("rel=0.82", rows[0]["measured"])
        self.assertIn("_emit_signal", rows[0])

    def test_evaluate_pure_no_writes(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse((Path(d) / "kill_observations.jsonl").exists())
            K.evaluate(self.NODE, sec=[], velocity={"total_works": 0, "per_year": {}},
                       markets=[], ts="t")
            self.assertFalse((Path(d) / "kill_observations.jsonl").exists())
            self.assertTrue(os.path.isdir(d))

    def test_offline_run_ok(self):
        s = K.run(live=False, write=False)
        self.assertEqual(s["live"], False)
        self.assertGreater(s["nodes"], 0)

    def test_short_query_strips_parenthetical(self):
        q = K.short_query("Quantum IP tollbooth (IonQ estate: 1000+ assets)")
        self.assertNotIn("(", q)
        self.assertIn("Quantum IP tollbooth", q)

    def test_query_override(self):
        q = K.node_queries({"id": "quantum_ip", "label": "Quantum IP tollbooth (x)"})
        self.assertEqual(q["openalex"], "quantum computing patents")

    def test_baseline_ratio_in_measured(self):
        rows = K.evaluate(self.NODE, sec=[{"form": "4"}] * 6,
                          sec_baseline={"med_form4": 2.0, "med_deal": 1.0},
                          ts="t")
        self.assertIn("vs_base=3.0x", rows[0]["measured"])
        self.assertEqual(rows[0]["verdict"], "TRIGGERED")

    def test_baseline_medians(self):
        doc = {"NVDA": [{"ts": "a", "form4": 15, "deal": 5},
                        {"ts": "b", "form4": 5, "deal": 1},
                        {"ts": "c", "form4": 9, "deal": 3}]}
        med = K.baseline_medians(doc)
        self.assertEqual(med["NVDA"]["med_form4"], 9.0)
        self.assertEqual(med["NVDA"]["n"], 3)


class TestKalshi(unittest.TestCase):
    DOC = {"events": [
        {"title": "When will nuclear fusion be achieved?",
         "sub_title": "", "category": "Science and Technology",
         "series_ticker": "FUSION",
         "markets": [{"last_price_dollars": "0.332",
                      "volume_24h_fp": "15", "liquidity_dollars": "0"}]},
        {"title": "Who wins the big game?", "category": "Sports",
         "series_ticker": "GAME", "sub_title": "",
         "markets": [{"last_price_dollars": "0.5", "volume_24h_fp": "9",
                      "liquidity_dollars": "0"}]},
    ]}

    def test_keyword_filter(self):
        from collectors import kalshi as KL
        rows = KL.parse_events(self.DOC, "nuclear fusion energy")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["venue"], "kalshi")
        self.assertAlmostEqual(rows[0]["p"], 0.332)

    def test_mid_from_bid_ask(self):
        from collectors import kalshi as KL
        m = {"yes_bid_dollars": "0.40", "yes_ask_dollars": "0.50"}
        self.assertAlmostEqual(KL.market_price(m), 0.45)

    def test_best_book_across_venues(self):
        thin = {"question": "q", "p": 0.7, "volume": 10.0,
                "liquidity": 0.0, "tier": "low-liquidity",
                "venue": "kalshi"}
        deep = {"question": "q", "p": 0.6, "volume": 5_000_000.0,
                "liquidity": 300_000.0, "tier": "high-liquidity",
                "venue": "polymarket"}
        r = K.pm_reading([thin, deep])
        self.assertEqual(r["venue"], "polymarket")
        self.assertEqual(r["reliability"], 0.82)


class TestSeedClaims(unittest.TestCase):
    def test_build_claims_counts(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "seed_claims", str(ROOT / "scripts" / "seed_claims.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from bneck2 import worlds as W
        claims = mod.build_claims(W.load_worlds())
        self.assertEqual(len(claims), 2 * len(W.load_worlds()["worlds"])
                         + len(W.load_worlds().get("incumbents", [])))
        clocks = {c["clock"] for c in claims}
        self.assertTrue({"expert", "pm", "equity"} <= clocks)


class TestBacktest(unittest.TestCase):
    PANEL = [{"date": "2026-0%d" % m, "ticker": t, "score": s,
              "forward_return": r}
             for m, (t, s, r) in
             enumerate([("A", 1.0, 0.05), ("B", -1.0, -0.04),
                        ("C", 0.1, 0.01), ("D", -0.1, 0.0)], start=1)]

    def test_positions_dollar_neutral(self):
        pos = BT.make_positions({"A": 1.0, "B": -1.0, "C": 0.1, "D": -0.1},
                                quantile=0.25)
        self.assertAlmostEqual(sum(pos.values()), 0.0)
        self.assertGreater(pos["A"], 0)
        self.assertLess(pos["B"], 0)

    def test_walk_forward_shape(self):
        rows, stats = BT.walk_forward(self.PANEL)
        self.assertEqual(len(rows), 4)
        self.assertEqual(stats["periods"], 4)
        self.assertIn("sharpe", stats)

    def test_calendar_annualization(self):
        # two dates exactly one year apart: ann ~= net return
        panel = [{"date": "2025-01-06", "ticker": t, "score": s, "forward_return": r}
                 for t, s, r in [("A", 1.0, 0.10), ("B", -1.0, -0.02)]]
        panel += [{"date": "2026-01-05", "ticker": t, "score": s, "forward_return": r}
                  for t, s, r in [("A", 1.0, 0.10), ("B", -1.0, -0.02)]]
        _, stats = BT.walk_forward(panel)
        self.assertFalse(stats["overlapping"])
        self.assertGreater(stats["annualized_return"], 0)

    def test_overlap_flag(self):
        # daily snapshots with 5d forwards overlap -> flagged provisional
        panel = [{"date": f"2026-01-0{d}", "ticker": t, "score": s, "forward_return": r}
                 for d, (t, s, r) in enumerate(
                     [("A", 1.0, 0.01), ("B", -1.0, 0.0)] * 3, start=1)]
        _, stats = BT.walk_forward(panel, horizon_days=5)
        self.assertTrue(stats["overlapping"])
        self.assertIn("sharpe_note", stats)

    def test_costs_reduce_net(self):
        _, free = BT.walk_forward(self.PANEL, cost_bps=0.0)
        _, paid = BT.walk_forward(self.PANEL, cost_bps=100.0)
        self.assertLessEqual(paid["annualized_return"],
                             free["annualized_return"])


class TestImplied(unittest.TestCase):
    def test_recovers_known_p(self):
        x = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
        y = [0.2, 0.8, 1.0]
        out = IM.infer_market_probabilities(x, y, ridge=1e-6)
        self.assertAlmostEqual(out["p"][0], 0.2, places=2)
        self.assertAlmostEqual(out["p"][1], 0.8, places=2)
        self.assertFalse(out["ill_conditioned"])

    def test_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            IM.infer_market_probabilities([[1.0]], [1.0, 2.0])


class TestObsolescence(unittest.TestCase):
    def test_decay_positive(self):
        self.assertGreater(OB.technological_obsolescence(100.0, 40.0), 0.0)

    def test_growth_negative(self):
        self.assertLess(OB.technological_obsolescence(40.0, 100.0), 0.0)

    def test_thin_base_none(self):
        out = OB.firm_obsolescence("F", 2026, 5, [], [])
        self.assertIsNone(out["obsolescence"])

    def test_firm_pipeline(self):
        back = [{"citing_firm": "F", "citing_year": 2020,
                 "cited_patent": "P1", "cited_owner": "O"}]
        fwd = [{"citing_firm": "O", "citing_year": 2020, "cited_patent": "P1"},
               {"citing_firm": "O", "citing_year": 2020, "cited_patent": "P1"},
               {"citing_firm": "O", "citing_year": 2026, "cited_patent": "P1"}]
        out = OB.firm_obsolescence("F", 2026, 6, back, fwd)
        self.assertEqual(out["base_size"], 1)
        self.assertGreater(out["obsolescence"], 0.0)


class TestPolywhale(unittest.TestCase):
    MKTS = [{"question": "Will X?", "conditionId": "0xabc", "p": 0.6}]

    def stub_holders(self, cid):
        assert cid == "0xabc"
        return ([{"wallet": "0x1", "outcome": 1, "amount": 5000.0}] * 1
                + [{"wallet": f"0x{i}", "outcome": 1, "amount": 2000.0}
                   for i in (2, 3, 4)]
                + [{"wallet": "0x9", "outcome": 0, "amount": 9000.0}])

    def test_consensus_finds_three_whales(self):
        from collectors import polywhale as PW
        out = PW.consensus(self.MKTS, holders_fn=self.stub_holders)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["outcome"], 1)
        self.assertEqual(out[0]["n_wallets"], 4)
        self.assertAlmostEqual(out[0]["total_usd"], 11000.0)

    def test_consensus_respects_min_usd(self):
        from collectors import polywhale as PW
        out = PW.consensus(self.MKTS, min_usd=6000.0,
                           holders_fn=self.stub_holders)
        self.assertEqual(out, [])

    def test_wallet_stats(self):
        from collectors import polywhale as PW
        orig = PW._get
        PW._get = lambda path, params: [
            {"currentValue": 100.0, "percentPnl": 10.0},
            {"currentValue": 200.0, "percentPnl": -5.0}]
        try:
            s = PW.wallet_positions("0x1")
        finally:
            PW._get = orig
        self.assertEqual(s["n"], 2)
        self.assertAlmostEqual(s["total_value"], 300.0)
        self.assertAlmostEqual(s["win_rate"], 0.5)

    def test_kalshi_candles_url_and_parse(self):
        from collectors import kalshi as KL
        u = KL.candles_url("KXELONMARS", "KXELONMARS-99", 1, 2)
        self.assertIn("/series/KXELONMARS/markets/KXELONMARS-99/candlesticks", u)
        rows = KL.parse_candles({"candlesticks": [
            {"end_period_ts": 10, "price": {"close_dollars": "0.11"}, "volume_fp": "5.0"},
            {"end_period_ts": 11, "price": {"close_dollars": None}, "volume_fp": "0"}]})
        self.assertEqual(rows[0]["close"], 0.11)
        self.assertIsNone(rows[1]["close"])

    def test_condition_id_passthrough(self):
        from collectors import polymarket as PM
        doc = {"events": [{"title": "T", "markets": [
            {"question": "Q?", "outcomePrices": "[0.6, 0.4]",
             "conditionId": "0xabc", "volume": "10", "liquidity": "1"}]}]}
        rows = PM.parse_markets(doc)
        self.assertEqual(rows[0]["conditionId"], "0xabc")


if __name__ == "__main__":
    unittest.main()
