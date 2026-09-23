# System v1 — Filtered Mirror (paper)

> Design constraints, honestly stated: no speed infra (lose every HFT
> race), small bankroll (maker-MM and calibration arb need $25k+),
> $9 Jev budget (every call must earn its information value).
> So the system uses the two edges that survive those constraints.

## Thesis

Bots win speed. Whales win capital. We win **reading**:
specialist flow (who wins, verified on-chain) filtered through
resolution analysis (what can go wrong). Each half covers the other's
fatal flaw — copiers die on Michigan/WMU events; divergence analysis
alone has no timing. Together: follow proven flow ONLY into cleanly
worded markets.

## Universe

- 3–5 tracked specialists (PEOPLE.md), single-category, 30d verified.
- Markets they enter that ALSO clear the divergence filter.
- Resolution-decay calendar as second leg (known schedule, enter
  early — not sniping, positioning).

## Entry (all must hold)

1. Tracked specialist opens/changes a position (Data API activity,
   free, no key).
2. Market divergence below threshold (clean text — exclusions and
   weasel scan from our records).
3. Spread + fees leave >1c net (0.75%/leg + gas math, computed not hoped).
4. No live UMA dispute, no pending resolution within 24h (avoid
   buying into an active rinse).

## Exit

- Specialist exits, OR
- dispute filed on the market, OR
- resolution reached, OR
- 50-position rolling paper PnL turns negative (regime check).

## Sizing (paper)

Fixed 1 unit per position. No compounding claims, no Kelly, no
martingale — not until 100+ paper positions with measured edge net
of fees. NORTHSTAR lesson 2 is load-bearing here.

## Success criteria (graduation to real money)

1. 100+ paper positions logged with entry rationale each.
2. Net edge after modeled fees > 0 with confidence intervals.
3. At least one full dispute cycle observed (watch one Michigan-type
   event resolve without us in it — tuition-free lesson).
4. Only then: smallest real size, one market, full receipt discipline.

## What each part costs

- Wallet tracking: $0 (Data API keyless).
- Divergence filter: $0 (deterministic code, already built).
- Resolution texts: $0 (Gamma keyless).
- Jev verdicts: ~$0.0002/call — budgeted ONLY for entries passing
  filters 1–4 above. No blanket re-scoring. The $9 lasts months
  at this burn rate.

## Backtest status (2026-09-23, `pm/backtest_mirror.py`)

First run (2 wallets × 300 older trades): n=30 resolved scored —
hit rate 33%, paper PnL **-5.07**; divergence-excluded subset n=5,
-1.13. Blind mirror loses net of fees on this sample. Caveats: no
position netting (scale-ins counted separately), 2 wallets, n=30.
Not a verdict on mirroring — a baseline the filter must beat.
Next: netting, more wallets, recency windows.

## Explicitly not in v1

Maker MM (needs $25k+), latency HFT (2.7s windows, need infra),
conviction long-dated (Sharpe 0.6, needs genuine info edge),
auto-disputes ($750 a pop, never).
