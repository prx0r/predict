# Strategies — what actually works on Polymarket (researched 2026-09-23)

> Sources: PolySyncer 18-month resolved-trade study, polymarkets.co.il MM
> guide, sovereign2013 post-mortem, pascal-labs SDK docs, official CLOB
> docs. Nothing below is backtested by us — treat as prior, not truth.
> Paper first. See JEV.md § Hallucination controls.

## The five shapes with 18-month Sharpe data

| # | Strategy | Sharpe | Capital floor | Notes |
|---|---|---|---|---|
| 1 | Resolution-window decay | 1.9 | attention (20–40 shots/mo) | Final-hour convergence as makers pull quotes; thin books, needs fast execution |
| 2 | Maker-rebate MM | 1.9 | $25k+ (spread+rebate math) | Max drawdown −1.4%; mechanical, uncorrelated; dies under adverse selection |
| 3 | Calibration arbitrage | 1.7 | $25k+ | 1–4pt systematic biases; fees eat sub-$500 sizing |
| 4 | Specialist mirroring | 1.4 | $2k+ | Follow 3–5 vetted single-category specialists; uncorrelated basket |
| 5 | Conviction long-dated | 0.6 | varies | Weakest; only with genuine informational edge |

## Three more patterns (documented, thinner data)

6. **YES/NO same-market arb** — combined price < $1 locks spread.
   sovereign2013 turned $1 → $3.3M on this (37k trades). Warning: bots
   take ~73% of arb profit now; windows shrank 12.3s (2024) → 2.7s
   (2026). Retail competes for scraps without speed.
7. **Latency arb on 5-min BTC Up/Down** — faster CEX feed (Binance/Bybit)
   vs Polymarket odds lag; hedge Yes/No for exits. Directly adjacent
   to our SafeTrade L2 + venue flow data.
8. **Cross-platform** (PM vs Kalshi, 3–8c edges) — bigger spreads,
   harder execution, different settlement. Matches our venue-of-truth
   weighting problem.

## Universal kill conditions (encode before sizing)

- Fill PnL over last 50 fills turns sharply negative → halt (regime changed).
- Last-trade jumps >2σ from rolling mean → pause 30s+ (adverse-selection spike).
- Inventory cap $50–200/market until months of proven profit; skew quotes to neutral.
- After CLOB taker fees (0.75%/leg) + gas, a 1.5c gross edge ≈ 0.6c net. Size the math, not the vibe.

## Where Jev gives edge (mapped to this stack)

1. **No-API surfaces** (`jev-ultrafast`): resolution monitoring, odds
   comparison, exchange notices. Browser output is untrusted input —
   parsed, never executed. APIs where they exist (Gamma/CLOB/Data are
   all keyless for reads); browser only where they don't.
2. **Specialist discovery** (guild thesis, NORTHSTAR #1): `blink` +
   `neo4jev` over wallet graphs to find concentrated single-category
   wallets; `forecasters.py` Brier calibration to weight them.
3. **Resolution-window sniper**: thin-book speed game — Jev browser
   agent watches resolution sources while the CLOB client holds quotes.
4. **Liquidity sensing** (`prism`): same absorption math as POW
   miner-pressure (resting depth vs incoming flow), applied to PM books.
5. **Sizing/judgment** (`jev-mcp`): bounded sizing per NORTHSTAR #2.
6. **Verification** (`canny`): every claimed fill/receipt resolves to
   an artifact. Prediction log before outcomes (`pm/experimentation/`).
7. **Context hygiene** (`fast-jev-compaction`, `winnow`): long
   monitoring sessions without context rot.

## Local references

- `/home/box/pm-stack/pm-official` — official signing client (never implement EIP-712 ourselves)
- `/home/box/pm-stack/pm-sdk` — paper mode sandbox (use first)
- `/home/box/pm-stack/pm-strategies` — 10-strategy study material
- `/home/box/pm-stack/pm-arb-pro` — WS + execution-lock patterns
- `pm/collectors/` — our live Gamma/Kalshi/Manifold readers
- Unavailable (404, repos gone): spfunctions edge-detector, Calidessens arb bot — patterns captured above from indexed docs.
