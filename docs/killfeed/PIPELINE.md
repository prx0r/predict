# Evidence-not-news pipeline (msg 21, section 12)

Bloomberg-style (dead end): NEWS -> sentiment -> stock.

Ours:

```
papers (OpenAlex velocity, TechToken convergence)
patents (Predictive Patentomics, acceptance abnormal returns)
benchmarks (frontier evals, J_t milestones: Navier-Stokes-class events)
model evals + GitHub (implementation evidence in dependency repos)
capex / hiring / scientist movement / startup funding
procurement / FDA trials / government programs
supply chains (spot, inventory, capacity)
earnings calls / insider activity / production data
         |
         v  (bneck2/updater.py fuse: lineage-collapsed, log-odds pool)
probability distribution over future worlds  (bneck2/worlds.py)
         |
         v  (world -> capabilities -> costs -> behavior -> demand ->
             revenue pools -> cash flows -> valuation)
economic consequences per incumbent
         |
         v  (P_you - P_market) x Impact x Duration
mispricing score -> OBSOLESCENCE_ARBITRAGE / WATCH / NONE
```

Why this wins as AI commoditizes analysis: earnings-summary, headline
sentiment, filings-extraction and basic industry research all go to ~zero
alpha (everyone's agents do them). What remains hard: propagating an
obscure result seven causal edges to 2032 economics. That propagation IS
this pipeline.

Jump process note: model capability as K(t+1) = K(t) + dK + J(t).
Milestones (10k agents / 88 hrs class) arrive as belief claims with
clock=hard, fuse through updater, reprice worlds first. Repricing can
precede commercialization by years — that lag is the trade.
