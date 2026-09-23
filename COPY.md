# Copy — wallet-copy edge, tools, and where we win (researched 2026-09-23)

> Our backtest says blind mirror loses (-5.07, n=30). This file is why
> filtered copy might still work, what to copy, and what everyone else
> already built (in `/home/box/pm-stack/pm-{whalefeed,smartmoney,consensus}`).

## Benchmarks (third-party, large-n)

- Polycopy 687K+ resolved trades: Copy Score 70+ filtered copies win
  **67.7%** (+5.76% avg P&L). Only **~23%** of wallets net profitable.
  Copy Score is a *veto* (after-costs), not a ranking.
- Stand COPYCAT (1,500 wallets, 5,000 strategies): 6 crypto / 2 sports /
  1 weather / 1 politics in top-10 copied. #1 (0xdxD crypto bot) went
  **inactive since March** — edge decays or wallets rotate. Our monthly
  re-rank protocol exists for exactly this.
- RN1: $7M lifetime sports quant, soccer-only, no meaningful dips.
  ColdMath: pure weather niche. Domain specificity == edge, confirmed
  by a third party running the same analysis.

## Tooling landscape (all free/keyless reads)

- `pm-whalefeed` (polyalerth): tiny terminal watcher, any wallet +
  platform-wide `--whales --min` feed. Deliberately no auto-copy
  ("fills at worse prices than the whale got is how people lose money").
- `pm-smartmoney` (doniwibowo): category filter + consensus engine.
- `pm-consensus` (Zach-Labs): ~115 top traders, consensus positions,
  quality signals for real-crowd-vs-one-whale.
- PolyPulse: 30s arb scan + NegRisk baskets + Telegram alerts (free tier).
- Polycopy: 500K wallets, Copy Score veto, auto-copy bots ($30/mo).
- Merlin: tags (Sniper/Contrarian), Theo4 $22M top, balthazar +217%.

## The key endpoint we were missing

`GET data-api.polymarket.com/trades?filterType=CASH&filterAmount=10000`
— platform-wide whale feed, no wallet list needed first. Our monitor
should poll this, not just tracked wallets.

## Where we win vs all of the above

Nobody scores **resolution text**. Copy Score vetoes on costs;
leaderboards rank on P&L; arb scanners watch books. None read the
conditions for carve-outs — our divergence engine is the only second
veto that catches Michigan/WMU-shaped risk *before* the mirror fires.
Stack, don't replace: Copy-Score-style cost veto × divergence veto ×
Jev judgment. Three independent filters must all pass.
