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

## E8. Speech-count — BACKTESTED, POSITIVE (2026-09-23, n=826 legs)

Screen: Jev confusion ≥0.60 AND question matches "say X" AND event
within 48h. Action: consume live transcript, count the word, trade the
matching leg. No probability model; the conditions are mechanically
verifiable once the speaker stops talking.

**Fade leg (adopted, paper).** Within one event's word-count family,
flag any Yes leg priced ≥ max(0.05, 4× family median) **and ≤ 0.95**;
buy the NO token at (1 − Yes price).

Pulled 34 resolved speech families, 826 legs (`pm/backtest_speech.py`):
- **Tradeable subset (Yes ≤ 0.95, No cost ≥ 0.05): 16 legs, 16 wins,
  staked 11.44, P&L +4.47, ROI +39%** net of the 0.75%/leg assumption.
- Confound test — fade EVERY leg: 574 legs, 66.6% hit, ROI **+1.7%**.
  The screen is worth ~23× the indiscriminate baseline. Hit rate is
  meaningless here (families are ~97% No); ROI vs baseline is the test.
- Never fade a leg above 0.95: 70 such rows, **0 wins, −0.11**. Those
  are the transcript-verified Yes legs — the other side of the trade.

Named cases: "Machado" Yes 0.87 → No paid 0.13, returned +0.87
(Nobel laureate nine days prior; narrative into a word count).
"Unaffordable Care Act" CNBC 0.20 → +0.19. "Biden" ribbon-cutting
0.22 → +0.21 (siblings all ≤0.01).

Caveats logged, not hidden: fills are last-trade-before-resolution
(the market's own last print implies a two-sided book, so the fill is
observable, but the peak premium would be worse); 9 of 16 wins come
from one SOTU, so effective independent n ≈ 4 events, not 16 legs.

**Live leg (blocked).** Needs a transcript feed (C-SPAN /
whitehouse.gov) + word-list matcher + speech calendar. First live
instance: Trump remarks at Xi Jinping's event, 2026-09-24, 21 legs,
median 0.15. No fade hit (no isolated outlier — top leg "China" 5+ at
0.515 vs next 0.42). The 4× screen misses high-median families where
every word is plausible; a percentile variant is in shadow only until
it has its own resolved sample. Note the weekly families trade at
40–67c spreads on $17–130 liquidity — unpriceable at size, and a
liquidity edge, not a confusion edge.

Naive version KILLED by construction: family hit rate ~2%. Buying
cheap Yes on names he "might" say loses 98c per dollar.

## E9. Winner-take-all joint markets — SPECCED, one validation (2026-09-23)

Nobel 2025 family: 39 markets, 5.1% Yes, mean Jev confusion 0.78,
misleading 0.57. Individual-name legs are lottery tickets (2 winners
across 78 resolved legs). The one structural exception: the JOINT
market "Will Trump and Machado share the Nobel Peace Prize?" resolved
**Yes** (confusion 0.80, regex divergence 8 — both instruments high)
while no individual-name market can express a shared award.

Play: in races that allow joint outcomes, price the combination legs
and fade the name legs. Needs a second joint-market validation before
any size; the divergence/judge agreement on that one record is the
screen, not the proof.

## E10. Ceasefire date-ladder level — KILLED as shape trade, kept as monitor (2026-09-23)

The 13-leg Russia–Ukraine ladder is a coherent survival curve:
constant hazard λ=0.0027/day (half-life 257d) fits all 13 legs,
SSE 0.013, max residual 3.2c. No calendar-arbitrage in the shape;
the "sell the December bump" idea nets −2c after the 0.75%/leg
assumption. E4 verdict extends to ladders: bots enforce coherence.

What survives: the LEVEL. Dated-ceasefire-leg base rate is 0/7 in
resolved history (Israel–Lebanon ×4, Israel–Hamas ×1, R–U May/June
×2 — the May truce resolved No on the mutuality test). Ladder prices
near legs 0.085 (Oct 31) / 0.14 (Nov 30). n=7 gives a 95% upper CI
of ~35%, so the near legs are *plausibly* fat, not provably fat.
Monitor the level; do not trade the curve.

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
