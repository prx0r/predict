# Trader-tracker repos — clone verdicts + recipes (2026-09-10)

Cloned shallow into `third_party/` (except 5 dead). Rule: read-only and
paper modes only. Nothing here places live trades from this box.

## Cloned + working live (keyless)

- `polytrack` (0xsteve-00/polymarket-tracker) — zero-dep Python, runs HERE.
  Verified: `scan`, `leaderboard`, `consensus` (found live 3-whale consensus),
  SQLite history. Recipe ported: `collectors/polywhale.py`.
- `polywhale` (EricSpencer00/polymarket-whale-tracker) — needs requests+
  websockets (no pip on box, not run). Recipe mined: Data API map
  (/positions /trades /activity /value /holders + CLOB /book /midpoint),
  algo-fingerprint features (sub-second clustering, both-sides hedging,
  sizing entropy), qualify thresholds (vol≥$1500, steadiness≥0.45,
  PnL window 7d). Port the fingerprint next, not the runner.

## Cloned, needs deps/keys (verdicts from review — no pip/npm haute here)

- `pmbot` (nerdyvinny) — best design of the lot: auto leader discovery +
  backtest-vetting ("profitable yet not copyable" filter), exits mirrored
  proportionally, PM↔Kalshi arb scanner with human-confirmed pairs +
  Kalshi fee math `ceil(0.07·C·P·(1−P))`. Needs httpx/pandas/pydantic.
  Port first when deps exist: vetting + exits logic + arb pair workflow.
- `pm-arb` (ImMike) — 10k-market monitor + dashboard + kalshi_client.
  Needs httpx/aiohttp. Review its pair-matcher before building our arb scan.
- `kalshi-ai` (ryanfrigo, 423★ MIT) — RSA auth + market data + order
  placement framework; no copy feature. Execution base if we ever go live.
- `kalshi-cli` (OctagonAI, 312★ MIT) — research→edge→Kelly→risk-gate
  pipeline. Kelly sizing matches our rank-sizing needs; port the math,
  not the runner.
- `kalshi-deep` (OctagonAI) — Octagon research layer. Inspect on arrival.
- `copy-sim` (ArslanKamchybekov) — needs ClickHouse/Redis/Node. Overkill;
  architecture notes only.
- `anthowave` / `sniperun` — need Mongo/Supabase + private keys. Skip
  running; patterns (tiered multipliers, aggregation windows) noted.

## Dead upstream (404 — deleted/renamed, not silently dropped)

`stackpathLab/polymarket-copy-trading-bot`, `ScouterInfinite/...`,
`ethuncledealer/polymarket-copy-trader`, `kalkiai-trade/kalshi-copy-trading-bot`,
`Cortex-Trading-Systems/...` (hype copy; no loss).

## What got integrated

1. `collectors/polywhale.py` — holders/positions/trades + N-whale consensus.
2. killfeed pm leg emits `WHALE_CONSENSUS` signals on the best-book market
   (bounded: 1 holders call/node).
3. Selection discipline (from gist + pmbot): winrate 60%+/100+ trades,
   multi-whale confirmation, slippage skip, exits mirrored — encoded as
   thresholds, not vibes.
4. Kalshi truth (AgentBets 2026-03): no public per-trader positions on
   Kalshi — copy there means leaderboard/order-flow inference, never
   true mirroring. We track Kalshi books, not Kalshi wallets.

## Next (needs deps or keys — queued, not faked)

- Backtest-vetting leaders (pmbot recipe) once pandas exists.
- PM↔Kalshi arb scanner on human-confirmed pairs (needs volume math live).
- Kelly sizing port (kalshi-cli recipe) into ranking.
- Algo-fingerprint port (polywhale features) into forecaster Skill.
