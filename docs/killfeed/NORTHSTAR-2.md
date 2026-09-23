# NORTHSTAR-2 — formal mathematical thesis for ORGO (2026-09-10)

Successor to goated.md (thesis v1: what matters) and ENDGAME.md (where it
goes). This doc is v2: **exact signal definitions, a DAG with measured
lags, and a backtestable alpha model** — written so a quant could implement
it without asking us anything. Predecessor docs stay valid; this tightens.

## 1. Universe (initial tester scope)

NVDA + OpenAI-counterparties + their insiders/SEC footprints:

```
NVDA, AMD, AVGO, MSFT, GOOGL, MU, ORCL, CSCO, CRWV, ARM
```

OpenAI is private: trade its validation chain (who it pays, who supplies
it, who insures its infra). BTC tracked as regime covariate, not position
(rho 0.02 — decoupled, E019).

## 2. Signal definitions (quant form — every S has units, cadence, lag)

For ticker i at decision date t (Friday close grid), all inputs dated ≤ t:

```
MOM(i,t)    = ret(t-20d, t)                                   [dimensionless]
BURST(i,t)  = N4(t-30d,t) / max(median_1y, 1)                 [ratio]
SELLUSD(i,t)= Σ insider sale USD(t-30d,t) / median_1y         [ratio]
BUYUSD(i,t) = Σ insider buy  USD(t-30d,t)  (NVDA: ≡0 observed)[ratio]
ATTK(n,t)   = prior-year OpenAlex growth, node(n)∋i           [ratio, lagged 1y]
HN(i,t)     = story count(t-90d,t) for node query             [count]
SHORT(i,t)  = FINRA short ratio, nearest tape                 [0..1]
PMBEST(i,t) = best-book p across venues on linked question    [0..1] + tier
WHALE(i,t)  = consensus USD on linked market                   [USD]
CONV(i)     = node conviction (static)                         [0..1]
B(i)        = node severity (static intraday)                  [0..+]
```

Normalization: cross-sectional z-score per date (no look-ahead, ever).
Signs from TRAIN only (predict.composite_by_date enforces).

## 3. Dependency DAG (measured lags, NVDA 17-week panel)

```
event ──0d──▶ price ──+3w──▶ HN echo ──+4w──▶ filings cluster
  │            │  r=0.69        │  r=0.75
  │            ▼                ▼
  │      PM reprices (min–hrs)  sales ride rallies (+3.4% heavy months)
  ▼
research attack (years) ──▶ migration ──▶ next bottleneck
```

Read it as plumbing: money moves first, narrative echoes, filings cluster
last. Trade the left edge for timing, the right edge for direction.

## 4. Alpha model

```
z(i,t) = Σ_f s_f · zscore_f(i,t) / k,   f ∈ winners(train IC>0.1, n≥40)
w(i,t) = quantile(z, 0.2)               # dollar-neutral L/S
r_net  = Σ w·fwd − turnover·10bps
```

Promotion bar (all three, holdout only): Sharpe(top-tercile long) > 0 AND
Sharpe(composite) > Sharpe(momentum) AND n ≥ 60. Current status: long tilt
+2.24%/window n=8 (directional); L/S loses less (−1.03 vs −1.93). NOT
PROMOTED. The bar is the boss.

## 5. Backtest discipline (point-in-time or it didn't happen)

- Monthly + biweekly grids; train m1–9/signs, holdout m10–12 (E014) and
  18/8 split (E015); per-date cross-sectional norms; costs on turnover.
- Reconstructed rows carry graph-sha + flag (backfill_panel.py).
- Red-team monthly (E013); burst-reversal killed twice (E015/E016 logic).
- Drawdown gate → BLOCKED (review machinery, not a result).

## 6. What each signal represents in ORGO (one line each)

MOM = crowd memory (bogey). BURST = regime attention (fade, don't chase).
SELLUSD = strength-exhaustion proxy. BUYUSD = conviction when nonzero.
ATTK = technological pressure direction. HN = saturation gauge. SHORT =
positioning both-ways flag. PMBEST = fastest belief. WHALE = staked
conviction. CONV/B = structural priors (slow, près-time-invariant).
BTC = regime covariate (currently decoupled — check quarterly).

## 7. Open upgrades (ordered)

1. Expand universe to atoms screen names with Yahoo coverage.
2. Kalshi-candle momentum factor (candles wired, factor unwritten).
3. CLOB depth-weighted reliability (collector live, unused in score).
4. pmxt implied-p → replace p_market placeholders (sharpens consistency).
5. Regime-conditional composites (drawdown vs expansion alphas differ).
6. E011/E007 maturation via cron (Oct).
