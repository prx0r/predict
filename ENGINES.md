# Engines — verdict log (backtested, adopted or killed)

> Rule: an engine lives here only with a backtest behind it. Paper
> numbers, fees modeled (0.75%/leg), no compounding claims. Killed
> engines stay listed — negative results are tuition already paid.

## E1. Blind mirror — KILLED as standalone (2026-09-23, confirmed n=123)

8 wallets × 300 older trades → 123 netted positions: **45.5% hits,
−4.92** (one wallet returned zero trades — dead address or API gap,
logged). Near coin-flip hit rate with negative expectancy = the fee
grind plus loss asymmetry; breakeven needs ~52%+ at these prices.
Two wallets scored zero (all-unresolved recent flow). Bugs caught en
route: VWAP divided price×size by itself (0% phantom), public-search
can't resolve conditionIds (use slug lookup).

## E2. Divergence filter — KILLED as standalone (2026-09-23)

Excluded (high-divergence) subset: n=5, 40%, −0.57. Also negative —
the filter doesn't rescue the mirror on this sample. Kept as a VETO
(research), not a strategy. Needs: bigger n, recency windows.

## E3. CopyScore-70 replication — QUEUED

Theirs: 67.7% wins on 687K trades with score-70+ filter. Ours: wallet
hit_rate + n now recorded per run (`wallets` in every mirror report).
Next: screen 8–10 wallets by trailing win-rate + min resolved count,
mirror only qualifiers, compare vs blind. This is the adopt-if-proven
candidate.

## E4. Set-sum basket — NO SIGNAL (2026-09-23)

Live books: max deviation 0.001 on sampled runs. Hurricane set 0.966
on last-trade needs book verification. Monitor watches; nothing fires.

## E5. Resolution decay — UNTESTED

Needs resolution calendar + price paths per decaying market. Data
exists (CLOB per-token paths dead; trentmkelly books selective).
Queued behind E3.

## E7. Fee model — OPEN (2026-09-23)

Flat 0.75%/leg is an assumption under fire: Gamma carries per-market
`takerBaseFee`/`feeSchedule`/`feeType` (e.g. politics_fees rate 0.04
taker-only, 0.25 rebate), distank uses 2% commission. Fee fields now
captured per backtest row; units TBD — do not convert until verified
against docs. Backtest P&L is fee-model-sensitive; treat all figures
as conditional on this assumption.

## E6. Jev copy loop — PAPER (2026-09-23)

2 paper entries logged (AI-rename No ×2 judges, Taiwan No). Awaiting
resolutions. Judge: edge realization on resolve, Brier vs market.
