# SYSTEM SPEC — how everything connects (spec-first, msg 23)

## 1. Asset inventory (2026-09-10)

**Zips:** `/tmp/bneck-full.zip` 178KB (49 files), `/tmp/bneck2-full.zip`
141KB + `bneck2/outbox/` copy. Engine+data+docs+messages only; clones
excluded (URL manifest in `docs/RESOURCES.md`).

**Repos:** stockify 454M (frozen fork core) · bneck 2.5G (engine v1 + 19
clones + Levin corpus + msg archive) · bneck2 5.9G (v2 engine + 6 clones).

**Data:** Levin metadata 675 entries/328KB + 118 PDFs (stockify);
graph_v2 16 nodes/13 edges; precedents n=9; readings; worlds (6+2);
deals 15 + commitments 11; diggers 3; FTO seed (IonQ); CEO ledger
(2 known, 2 gaps); forecaster priors; x-thinkers roster.

**Clones (22):** bneck/third_party = 19 (prophetmap→thrml, incl.
ai-release-radar, Qwen-MetaZenith); bneck2/third_party = 6 (pmxt,
graphiti, edgartools, arxiv-trend-radar, jobseek, patents-assistant).

## 2. The seven graphs and their dependencies

```
corpus (genius attention) ──┐
labs (revealed preference) ─┤
collectors (SEC/GitHub/     ├─> belief (claims, 4 clocks, lineage)
  OpenAlex/PM/USAspending) ─┘         |
                           forecasters (Skill_i weights expert clock)
                                      v
physical dependency graph <── updater (Bayesian fusion, J_t milestones)
   |  (nodes/temporal edges, Tk/Td, DESTROY/CONSTRAIN)
   +── quant (conviction, regimes, RedundancyRisk, ShortConvexity)
   +── criticality (N-1 removal: whose loss breaks most value)
   +── jevons (SUBSTITUTION vs EXPANSION gate on every KILL)
   +── patents/FTO (legal betweenness; tollbooth share)
   +── worlds (P_you vs P_market -> Signal_company, obsolescence screen)
                                      v
                          status briefs (board / quant / belief / revealed)
```

Dependency rules:
- Nothing downstream of corpus/labs/collectors runs without them; they
  are the only writers to belief claims.
- Edge weights change ONLY via updater.fuse (lineage-collapsed) or
  milestone_event (J_t jumps, prefixed, auditable).
- Kill-signals fire ONLY from kill_observations verdicts + digger L4+
  (never from hype, never from single uncorroborated claims).
- Shorts require: binding status + crowdedness>=0.7 + kill_ratio>0 +
  Jevons=SUBSTITUTION. All four, no exceptions.
- CEO ledger never mixes known/unknown; forecaster priors start n=0.
- Stockify boundary (peer-review P1 fix): killfeed emits Evidence
  (kill_observations rows), Claims (belief claims), Predictions (with
  resolution functions), Experiments (receipts), WorldDeltas. Stockify
  decides attention/ranking/delivery and NEVER adjudicates causal truth.
  Killfeed never does UI, feeds, or ranking-for-humans. Contract objects
  are the JSONL/JSON files both sides already share; no new API needed.

## 3. All weightings in one place

| Quantity | Formula | Lives in |
|---|---|---|
| conviction | 0.5·prev + 0.3·(1−crowd) + 0.2·evidence | graph.py |
| short_score | crowded·(0.3+0.7·kill_ratio), binding only | graph.py |
| LabSignal | log1p($)·irrev·spec·rel·dur | labs.py |
| RedundancyRisk | P(agi)·P(deploy)·purity·lev·yrs (normalized) | quant.py |
| ShortConvexity | redundancy·crowded/(1−crowded+0.2) | quant.py |
| Criticality(v) | Σ dependents weight/depth (N-1) | graph.py |
| Signal_company | Σ(P_you−P_market)·Impact·Duration | worlds.py |
| Skill_i | Laplace-pooled calibration/lead/spec/novelty/indep | forecasters.py |
| reliability | (hits+1)/(n+2), priors flagged n=0 | calibration.py |
| fuse | log-odds pool, prior weight 1, roots only | updater.py |
| jevons | residual=(1−gain)·elasticity; <1 SUBSTITUTION | jevons.py |
| Tk/Td | Td·2≤Tk LONG-WINDOW; Tk≤2 CLOSING | quant.py |
| scarcity scan | keyword hit on label+kill/destroy phrases; tickers from node | scarcity.py (PORTED_MAP ex-stockify detector) |
| AttackIntensity | growth=recent-2 COMPLETE years vs prior 2 (current year excluded); HIGH needs growth≥1.0 AND total≥200 | killfeed.py |
| AttackIntensity source | group_by=publication_year counts (NOT the 50-row sample page); ok=False → INCONCLUSIVE; label-derived queries + QUERY_OVERRIDES | collectors/openalex.py, killfeed.py |
| SEC burst | NEW accessions since last poll only (accession ledger; never re-counts) | killfeed.py, data/beliefs/sec_seen.json |
| SEC cadence | per-ticker history (cap 30) → vs_base ratios in measured; verdict unchanged | killfeed.py, data/beliefs/sec_baselines.json |
| PM venues | Polymarket Gamma + Kalshi open-events (keyword match), best book wins | collectors/polymarket.py, collectors/kalshi.py |
| PM queries | topical overrides (AGI-2027, nuclear, robot…) — labels return noise | killfeed.py PM_QUERY_OVERRIDES |
| pm reliability | single home calibration.pm_reliability (0.82/0.60/0.50 priors, n=0) | calibration.py |
| acq event study | 20d fwd vs SPY per dated lab deal; drops logged | bneck2/acq.py (H-ACQ-1 refuted → H-ACQ-2/3 refine) |
| XBRL revenue | tag-rename aware series (Contract→Revenues→Sales) | collectors/sec_facts.py |
| whale consensus | N+ wallets same outcome ≥$1k → WHALE_CONSENSUS signal (best-book mkt, 1 call) | collectors/polywhale.py (recipes ex-polytrack/polywhale) |
| pm evidence grade | linked (typed market→node edge in pm_links.json) vs discovery (logged, never fused) | killfeed.py, data/pm_links.json |
| IO boundary | run()+collectors do I/O; evaluate() pure (AST + socket-kill tested) | tests/test_purity.py |
| lifecycle | EXPLORATORY for searches (comparisons>1 can't CONFIRM); mutations get new IDs | lab.py |
| lab receipts | preregister → run → receipt → verdict; n<30 directional-only | bneck2/lab.py, experimentation/ (cg-flow) |
| forward returns | Yahoo daily closes; close-to-close over N trading days | bneck2/prices.py history() |
| fundamentals | XBRL companyfacts: rev TTM, growth, R&D intensity | collectors/sec_facts.py |
| HN heat | stories≥10 & pts≥500 HIGH (saturation cross-check) | collectors/hn.py |
| Manifold | 3rd pm venue, same tiers (triangulation) | collectors/manifold.py |
| bioRxiv | preprint keyword counts per window | collectors/biorxiv.py |
| HF heat | model/like counts per query (implementation) | collectors/hf.py |
| SemScholar | 429-aware 2nd paper source (retry 0/2/8s, else OpenAlex carries) | collectors/semscholar.py |
| lab RSS | OpenAI + DeepMind capability posts × node scan → lab_node joins | collectors/labs_rss.py |
| connections | burst×drift, attack×narrative, whale×node, pm-spread, sev×price | bneck2/connect.py |
| backtest panel | snapshots append idempotent; forwards fill; <2 dates INSUFFICIENT | bneck2/backtest.py, data/backtest/panel.jsonl |
| oneclick | all streams → report, graceful degradation per step | scripts/oneclick.py |
| senate-blocked | efdsearch 403s bots; needs session/key — unknowns ledger | docs (queued) |
| advice | a=s·c, dust 0.10, sequences OPEN→FILLED→CLOSED | advise.py (NORTHSTAR-5) |
| E044 | sized loses to full-size (map too timid — mutate it) | experiments |
| E045 | short_fade Sharpe 0.82 beats 3x-bh 0.42 on NVDA test yr (return trails) | experiments |
| E046 | rules do NOT generalize cross-sectionally (REFUTED) | experiments |
| E047 | forward paper test, 90 days, logging daily | scripts/paper.py |
| E048 | fish bounce rule REFUTED (-0.65 vs bh +0.87; their 62% was artifact) | experiments |
| E050 | NVDA-mimic REFUTED directional (-2.87% vs SPY -2.18% since 8/14 filing) | experiments |
| G001 | graph P0 bar (70% evidenced/30% quantified); baseline 8%/15%, 14 quarantined | edges.py |
| edge | typed REQUIRES schema; unknowns=None; tickers off physical nodes | edges.py |
| G002 | ProphetMap 27 layers -> PML_ nodes, 89 tickers as suppliers[] | prophetmap_import.py |
| edge-update | filings bursts + FINRA short-vol -> supplier evidence/crowdedness | edge_update.py |
| short-vol | FINRA feed is short-sale VOLUME share (~0.38 typical), not short interest | edge_update.py |
| propagate | shock x elasticity x grade-conf x damping x delay-weight over DAG | propagate.py |
| E051 | reflexivity via R&D REFUTED (rho=-0.00; validated +17% < unvalidated +51%) | experiments |
| E052 | reflexivity via capex REFUTED (rho=+0.20 arrow real, trade loses +22%<+39%) | experiments |
| E053 | step-obsolescence basket REFUTED (IGV +6.7% post-events; only DeepSeek dented) | experiments |
| observation | OBSERVATION primitive; 9 families routed to edge/node fields | observation.py |
| actors | 34-actor registry, seed-unverified, no spend yet | actor_registry.json |
| G003 | death-watch: feedify researcher threats -> THREATENS overlay (>=10) | threat_extract.py |
| death-watch | shock PML_L0 -> THREATENS-ranked exposure + evidence-depth tiebreak | propagate.py |
| triage | DYING/UNPRICED/QUESTIONED buckets vs SPY since first threat | threat_triage.py |
| bearcase | boolean bear trees; P=TRUE-wt/RESOLVED-wt; manuals stay null | bearcase.py |
| attribution | return = market + layer + idio (R2); score-drift/PEG/funnel divergence flags | attribution.py |
| concepts | one thesis per CONCEPT_GROUP; crash rank = role + low-moat + threats | concepts.py |
| E054 | death-watch basket REFUTED (+1.3%, t=0.52); value in DYING subset only | experiments |
| DW-fwd | re-run triage+E054 at 90d = forward leg | threat_queue.json |
| BODYCOUNT | 2022-11-30->now: CHGG -184pp, FVRR -161, CNXC -165, FIVN -139, UPWK -118, FRSH -107, DUOL +19 | exhibit |
| PAPERS | 15-paper obsolescence review (AMH, AI premium, inflection, commoditization) | PAPERS-OBSOLESCENCE.md |
| E055 | AI-beta LONG REFUTED (-2.6%/w, Sharpe -1.15; inverse worked, unclaimed) | experiments |
| E056 | aiContribution L/S CONFIRMED directional (+4.4%/q, n=82 names) | experiments |
| E057 | moat shield REFUTED directional (-4.6%/q; moats lagged) | experiments |
| E058 | AGI-proof rating REFUTED (rho=0.18<0.3; extremes rank right) | experiments |
| agiproof | structural 0-100: complement+moat-substitution-laborarb | agiproof.py |
| CHGG | existence proof: -77% excess 1y post-ChatGPT; mechanism lives at names, not basket | exhibit |
| fish-ml | conf>0.8 adds nothing over BUY baseline (62.5 vs 62.2); HOLDs auto-wrong | third_party/fish |
| secret gate | pre-commit grep (seed0 Rule 0/5) | scripts/check_secrets.sh (+suite) |
| NVDA ladders | 123 markets; resolved 39/39 calibrate | E042 |
| NVDA stack | X+SEC co-occurrence empty; solo +3.6% vs base +2.5% | E043 |
| reason bandit | 6 lenses, Boltzmann picks, rewards in data/lab/bandit.json | reason.py |
| rediscovery | 3 blind checks, all surfaced 2026-09-10 | experimentation/rediscovery.json |
| MCP server | stdlib JSON-RPC stdio: 13 tools over engine | scripts/mcp_server.py |
| headless battery | initialize→list→13 calls incl. errors, 0 failures | scripts/mcp_test.py (+suite) |
| sweep | full chain per ticker: SEC/insiders/holders/short/PM/whales/HN/EFTS/facts | scripts/sweep.py, docs/SWEEP-*.md |
| nasdaq holders | 6k holders/ticker + accumulators + insider counts | collectors/nasdaq.py |
| insider refs | canonical where-to-get-it per family | docs/INSIDER-REFERENCES.md |
| universe | 30 tickers, Yahoo-verified (15 graph + 15 atoms) | predict.UNIVERSE |
| CLOB depth | ±0.1 reliability on $1M depth / 0.2 spread | killfeed pm_reading |
| kalshi momentum | 7d carry on top-3 liquid (INCONCLUSIVE n=2) | E034 |
| X scout | gateway+ledger, recon gate, history, extractor, outcomes | xscout/xextract/x_backtest, E033 |
| X verdict | 76 calls 5d +0.33% — below bar, REFUTED (dnystedt carries) | E033 |
| deep panel | weekly 2y x6, point-in-time; FINRA tapes cached forever | build_deep_panel.py |
| E029-E031 | deep screen (mom survives) → momentum-only +1.07 vs bh -1.60 | experiments |
| divergence | insider buys into weakness beat strength-buys (E025 directional) | experiments |
| pre-disclosure | trade→filing vs filing→+5d drift split (E026) | experiments |
| ESPP gates | <$10k drop, ≥80% same-date+price reject (needs ≥3 rows) | experiments E027 |
| distance-high | near-high buys beat far buys (E028 directional) | experiments |
| lead-lag | xcorr ±4w; SEC→price +4w/-0.32, price→HN +3w/0.69, HN→filings +4w/0.75 | leads.py, E021-E024 |
| organism order | prices≈PM > whales > filings > HN echo > build > labs > research > permissions > macro | docs/ORGANISM.md |
| source graph | 27 nodes (25 LIVE), validated both directions | scripts/sources_graph.py, data/sources/graph.json |
| NVDA/OpenAI/BTC focus | insider buys=0 (all sells); BTC-NVDA rho 0.02 decoupled | E018-E020 |
| BTC history | CoinGecko daily closes, cached | prices.crypto_history |
| BTC calibration | live level markets snapshot, 7d resolve | E020, data/predict/btc_levels.json |
| threads ledger | live counts (unknowns/hyps/preds) vs THREADS.md --check | scripts/threads.py |
| predict panel | monthly 180 + biweekly 360 rows; point-in-time features only | predict.py, data/predict/ |
| factor screen | Spearman IC + Wilson; train m1-9/signs, holdout m10-12 | experiments E014/E015 |
| composite | per-date z-scores, signs from train (no look-ahead) | predict.composite_by_date |
| acq backtest | 20d fwd vs SPY per dated lab deal; drops logged | acq.py, E010-E012 |
| run files | immutable per-run inputs+outputs; receipts index them | lab.run_file, experimentation/runs/ |
| content cache | sha-keyed free replays (yahoo daily, openalex weekly) | lab.cache_*, data/cache/ |
| rebuild gate | delete projections → rebuild byte-equal (CI) | scripts/experience_build.py --check |
| sealed eval | eval-side modules import no live/runner code (AST-tested) | tests/test_cg.py |
| backtest gate | maxDD <= -50% → BLOCKED (review machinery, not a result) | backtest.live_result |
| experience db | derived sqlite projection (rebuildable, deletable) | scripts/experience_build.py |
| heartbeat | pass writes data/heartbeat.json; >30h gap shouts (no silent stops) | scripts/oneclick.py |
| backfill | reconstructed scores (graph sha labeled) + real Yahoo forwards | scripts/backfill_panel.py |
| red-team | monthly anti-case vs top conviction, scored like any hyp | experiments.E013 |
| predictions | preregister + resolve-due (temporal validation clock) | lab.predict/resolve, bneck2/resolve.py |
| obsolescence | −[ln Cit_t − ln Cit_{t−w}] on fixed external base | obsolescence.py (ex-kernel, exact Ma) |
| implied p | min ‖Xp−y‖²+ridge‖p−prior‖² s.t. [0,1], projected-gradient | implied.py (ex-kernel ridge) |
| backtest | calendar clock: asof/entry(next-close)/exit, annualize from elapsed days, overlap flagged provisional | backtest.py |
| LabSignal tiebreak | irrev·spec·rel·dur orders $‑unknown ties (no fabrication) | labs.py |
| scarcity B_i | induced·indisp·repl_norm·(0.5+0.5·perm)/(sub+eps); perm priors §5-6 | migration.py |
| dB/dt, accel | severity velocity + 2nd diff across severity_history.jsonl | migration.py |
| cross-world X | Σ_s P_you(s)·need_i(s), need=1−survival | migration.py |
| P_release | Laplace supply-verdict rate (self-dug only, never arch kills) | migration.py |
| catalytic | CATALYZES edges; h_B'=h_B·(1+Σ strength·event) | migration.py |
| derivative | DEPENDS_ON dependents + CASCADE unlocks if relieved | migration.py |
| alpha_v2 | gap·dCF·X·B·R − C (master eq, thesis §40) | migration.py |
| transfer weight | benchmark 0.30 … verified_cashflow 1.00 (mineability-aware) | migration.py |
| three clocks | t_capability/t_deployment/t_cashflow on claims (null till measured) | seed_claims.py |
| inconsistency | gap·p_market(w) where market prices survival + killing world | consistency.py |
| atoms convexity | mean(B)·(1+0.25·(breadth−1))/log10(rev)·(1−0.5·crowd) | atoms.py |
| deliverable MW | announced·P(site)·P(ix)·P(xfmr)·P(gen)·P(permit), missing→0.5 flagged | migration.py |
| surprise | logit⁻¹(logit(prior)+credibility·LLR_residual) | migration.py |
| cliffs | proximity=current/threshold; robot $4/h, inference $0.03, assay $1 | migration.py |
| duration mismatch | H_val−H_tech ≥2 → SHORT_CANDIDATE; missing → INSUFFICIENT | migration.py |

## 4. Thinker roles → graph functions (msg 23)

- Hypothesis generators (Levin, Bach, Walker, Mostaque): write world priors + DESTROY paths. Low initial clock weight, high novelty.
- Experimental bets (Verdon, Normal, Cronin, Kagan, FinalSpark): advance digger ladder; their milestones are J_t candidates.
- Change detectors (Raschka, D. Patel, Lambert): implementation evidence; highest evidence weight per claim.
- Builders (Fei-Fei, Hassabis, Rodriques): embodiment/science-loop nodes; CONSTRAIN paths.
- Allocators (Aschenbrenner, labs via deals): adversarial benchmark + revealed preference.
- Instruments get low ontology weight, HIGH evidence weight. Never average roles together.

## 5. Master loop (executable)

New capability → old constraint disappears (updater stamps valid_to,
opens successor edge) → activity explodes (prices/volume feed) →
next scarce input exposed (criticality re-ranks) → capital floods
(labs deals + commitments) → new technology attacks it (digger ladder
+ OpenAlex velocity) → scarcity migrates again (regime flips,
dissolution board re-ranks). Loop output twice daily; kill-feed continuous.

## 6. Build queue (in order)

1. ~~Kill-observations writer wired to collectors~~ DONE 2026-09-10:
   `bneck2/killfeed.py` + `scripts/killfeed.py` (SEC burst, OpenAlex attack,
   pm clock → verdict rows; live collection best-effort, evaluation pure).
2. ~~OpenAlex velocity per node~~ DONE 2026-09-10: AttackIntensity numbers.
3. ~~pm clock~~ DONE 2026-09-10 (Gamma venue data; pmxt adapter still queued).
4. edgartools-backed filing ingestion for backlog/language diffs.
5. graphiti-style valid_from/valid_to enforcement on regime flip.
6. ~~Backtest harness~~ DONE 2026-09-10 stdlib port (`bneck2/backtest.py`);
   90-day live-brief accumulation still needed before it means anything.
7. Rivera-style drift detection on regime time series (river, when pip exists).
8. Kernel remainder: TechToken / convergence / patentomics / MIRAI /
   supplychain (need embeddings + corpora; papers only for now).
9. Queued from goated.md (need feeds not code): usage telemetry
   (OpenRouter-style task×cashflow map), actor/reaction graph, reverse-DCF
   pair mining, ResearcherAlpha (needs semantic novelty), geo layer
   (company×site×permission), market-ensemble P_market.
