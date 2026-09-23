# NORTHSTAR-5 — confidence-weighted advisory engine (2026-09-10)

## The idea (user's, formalized)

The AI maintains a **sequence** of buy/sell advice per holding. Every price
update moves confidence; confidence sizes the advice. A full-conviction
sequence says "sell 100%, rebuy at $X" — but a 0.3-confidence engine
recommends selling 30%, so weak signals can't cause big misses. Confidence
itself comes from measured past performance (Wilson lower bounds, not vibes),
further weighted by fundamentals + macro context.

## Formalism

```
signal s(i,t) ∈ [-1,+1]     composite z-score, per-date cross-section
confidence c(i,t) ∈ [0,1]   min over active families of Wilson-lower hit rate,
                            mapped: c = clamp((lo - 0.5) * 4, 0, 1)
                                    (lo=0.5 → 0, lo=0.75 → 1)
advice a(i,t) = s · c       fraction of position to trade this window
thresholds: |a| < 0.10 → HOLD (dust filter); else SELL/BUY a×position
buyback: rebuy when s flips sign OR price retraces to trailing reference
         (20d low for sells); partial fills scale with |a| again
```

Sequence property: advice is a persistent object per holding (open → filled
→ closed), updated each window — never a one-shot call. History of advice
vs outcomes feeds c(t) back (the loop in ENDGAME.md, now with teeth).

## Family confidences (measured today, not assumed)

| Family | Evidence | Lower bound | c |
|---|---|---|---|
| momentum (up-regime) | E041 IC +0.14 n=480 | ~0.55 est | ~0.2 |
| supplier validation | E012 0.75 n=9 | ~0.35 | 0.0 (n too small) |
| whale consensus | E004 2/3 | ~0.21 | 0.0 |
| divergence buys | E025 directional | ~0.3 | 0.0 |
| X calls | E033 refuted | — | 0.0 (excluded) |

Rule: families below c>0 contribute NOTHING (multiplied out). This is how
"not very confident → 30% → 0%" happens mechanically.

## Backtest protocol (E044)

Sized (a=s·c) vs full-size (a=s) vs buy-hold, same dates/costs, biweekly
panel. Win condition: sized Sharpe > full Sharpe with lower drawdown
(sizing should cut tails, not just returns). If sizing underperforms,
confidence mapping is wrong — mutate the map, not the signals.

## Brainstorm (parked, priced)

- Buyback levels from support clusters (needs price-level memory — extend
  panel with 20d/60d lows; cheap).
- Fundamentals weight: XBRL growth × margin as slow multiplier on c.
- Macro gate: Treasury-rate regime doubles/halves c (risk-on/off).
- Per-holding sequences in signals.jsonl-adjacent `advice.jsonl` store.
- fish app surface: advice cards with fraction + rebuy + rationale +
  confidence bar (their UI, our engine output format).
