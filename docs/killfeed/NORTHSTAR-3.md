# NORTHSTAR-3 — how it all relates + how to use it (2026-09-10)

Supersedes nothing; unifies goated.md (what matters), NORTHSTAR-2 (formal
spec), ENDGAME.md (where it goes), ORGANISM.md (who moves first). Read
this file to operate the system; read those to understand it.

## 1. Northstar audit (v2 commitments → status)

| # | NORTHSTAR-2 commitment | Status |
|---|---|---|
| 1 | Expand universe to atoms names | HIT (15→30, Yahoo-verified) |
| 2 | Kalshi-candle momentum factor | HIT as E034 (INCONCLUSIVE n=2 — thin books, honest start) |
| 3 | CLOB depth-weighted reliability | HIT (±0.1 on $1M depth / 0.2 spread) |
| 4 | pmxt implied-p | MISSED (blocked, no adapter) — still the biggest gap |
| 5 | Regime-conditional composites | MISSED (queued; halves tracked in E031) |
| 6 | E011/E007 maturation | WAITING (cron + Yahoo history) |
| Bar | Sharpe>0 + beat momentum + n≥60 | NOT PROMOTED (best: +2.24%/window n=8) |

## 2. The relational model (entities × relations)

```
STREAMS (27, graph.json) ──measure──▶ SIGNALS (per node/ticker/date)
    │                                        │
    │ lead-lag (ORGANISM.md)                 ▼
    ▼                                  HYPOTHESES (preregistered,
VARIABLES (registry)                       falsifier-first)
    │                                        │ run → RECEIPT
    ▼                                        ▼
PANELS (monthly/biweekly/deep) ──screen──▶ WINNERS ──composite──▶ BOARD
    │                                        │
    ▼                                        ▼
BACKTEST ◀── forwards mature ── PREDICTIONS (resolve-due)
    │
    ▼
REFLECT → mutate → new HYPOTHESES (loop closes)
```

Relation rules (enforced, not suggested):
- Every SIGNAL names its stream + timestamp (no orphans).
- Every HYPOTHESIS names its falsifier + data (no vibes).
- Every RECEIPT is immutable; mutations are new rows.
- Every PANEL row is point-in-time (nothing dated after its window).
- Every PROMOTION needs holdout + bar (NORTHSTAR-2 §4).
- Every REFUTE retires ≥1 possibility permanently (dead lists kept).

## 3. How to use all this (operator routines)

**Daily (cron, automatic):** oneclick pass → verdicts, severity, experiments,
connections, resolve-due, panel append, report. Check: heartbeat fresh,
no FAIL lines, threads --check green.

**Weekly (15 min):** read latest ONECLICK report + experiment report.
Questions: new TRIGGERED cells? verdicts concentrated or spreading?
support rate tightening? panel completeness +1? Any INCONCLUSIVE that
graduated to decided?

**Monthly (1 hour):** re-probe PM queries (books move); review bandit
state (which reasoning arms pay); red-team E013; check predictions due;
retire dead variables (3 strikes); propose 2+ new variables from
residuals (Phase 0 agent job).

**Quarterly (half day):** full holdout re-run (E014/E015/E031); E007 panel
check (10+10 windows?); acq-chain rerun on new deals; consistency rows
re-read post-pmxt; backtest significance check (TARGET-90D #1); reflect
memo with redirect.

**Decision tree:**
- New signal idea → preregister (E-series) → run → receipt.
- CONFIRMED directional → needs n≥30 + holdout → else stays directional.
- REFUTED → retire direction, log mutation or close.
- Composite beats bogeys 2 consecutive holdouts + n≥60 → promote to board
  weighting (currently: NOT PROMOTED, board is tilt-only).
- Anything needing money/keys/judgment → THREADS.md human list.

## 4. Current readings (2026-09-10 refresh)

- Triggers: NVDA burst quiet under ledger (0 new); optical SEC + research
  attack holding.
- Momentum is regime-conditional: IC +0.14 up-months / -0.12 down-months
  n=660 (E041 CONFIRMED) — explains E031 halves; composites must gate on
  regime (NS-2 #5 HIT).
- Implied-p unidentified in general BUT our 2-incumbent instance is pinned
  by degenerate survives maps (E039 refuted as stated — need incumbents
  with different footprints, sharper requirement than 'more instruments').
- Promotion bar: NOT PROMOTED (tilt -0.023, comp -1.62 vs mom -6.04, E040).
- Cron ran 06:18 UTC daily; heartbeat live.

## 4b. Previous readings (kept for audit, superseded above)

- Triggers: NVDA burst, optical SEC + research attack (holding).
- Best shape: long-only tilt +2.24%/window (n=8, directional).
- Strongest single factors: conviction +0.33, momentum +0.22 (train).
- Whale consensus 2/3 resolved; X calls REFUTED (n=76, +0.33% under bar).
- BTC decoupled (rho 0.02); venues segmented (no fuzzy arb).
- Support 0.38 [0.21, 0.59]; backtest Sharpe 3.65 (n=3, directional).
