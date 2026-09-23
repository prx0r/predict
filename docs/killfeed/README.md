# bneck2 — revealed preference + diggers + collectors

Second-generation bottleneck engine. Everything in bneck v1, plus the
msg-20 architecture: frontier-lab capital commitments scored as revealed
preference, experimental-digger proof ladder, patent FTO mapping,
executive-capital OSINT (known vs unknown), and starter collectors.

Stdlib only. $0 data. No keys required (GitHub token optional).

## Layout

```
bneck2/           engine (v1 + labs/LabSignal, diggers, patents, ceo,
                worlds/Signal, scarcity, killfeed, backtest, implied,
                obsolescence, migration, consistency, atoms, kernel_bridge)
data/universe/    ai_atoms.json (test/measurement/certification universe)
collectors/       sec, sec_facts, openinsider, finra, github, openalex,
                crossref, biorxiv, semscholar, polymarket, clob, polywhale,
                kalshi, manifold, hn, hf, bio, fed, jobs, labs_rss,
                usaspending, grants
data/labs/        deals.json, commitments.json, diggers.json, ceo.json
data/patents/     fto.json (IonQ estate seed)
data/bottlenecks/ graph_v2.json, precedents.json, readings_*.json
data/beliefs/     forecasters.json, claims.json, kill_observations.jsonl,
                unknowns.json, signals.jsonl
data/corpus/      levin_metadata.json
data/worlds/      worlds.json (6 worlds + incumbents, p_you vs p_market)
imported/         postagi_kernel + resource_pack (flattened, pristine in imports/)
scripts/poll.py   5-min $0 snapshot
scripts/status.py board + --quant + --belief + --trigger
scripts/revealed.py LabSignal ranking + diversification + diggers + FTO + CEO
scripts/killfeed.py collect (opt --live) -> evaluate -> verdict-log loop
scripts/migration.py severity/velocity/X/derivatives/consistency board
scripts/experiment.py list|run|report (hypothesize→receipt→verdict lab)
scripts/build_predict_panel.py [--biweekly] (price-signal panel)
scripts/experience_build.py [--check] (rebuildable derived store)
scripts/oneclick.py (ONE command: poll→killfeed→migrate→experiments→
  connections→backtest→report docs/ONECLICK-<ts>.md)
experimentation/ hypotheses + receipts.jsonl + notes (cg-flow)
data/bottlenecks/severity_history.jsonl (dB/dt compounds per live pass)
scripts/seed_claims.py worlds.json -> claims.json (seed-tagged, idempotent)
outbox/           zips staged for email delivery
```

## Use

```bash
/usr/bin/python3 scripts/poll.py
/usr/bin/python3 scripts/status.py --quant
/usr/bin/python3 scripts/revealed.py
/usr/bin/python3 scripts/killfeed.py [--live] [--max-nodes N]
/usr/bin/python3 scripts/seed_claims.py [--force]
/usr/bin/python3 -m unittest discover -s tests   # count in docs/STATE.md (generated)
See docs/RESOURCES-CANONICAL.md for the live-vs-not source map.
```

## Key formulas

LabSignal = log(1+$) x Irreversibility x Specificity x Relevance x Duration
ShortConvexity = RedundancyRisk x crowded / (1 - crowded + 0.2)
Criticality(v) = Throughput(G) - Throughput(G-v)  [N-1 removal]

## Proof discipline

Diggers advance CLAIM -> SILICON -> PEER_REVIEW -> INDEPENDENT ->
NORMALIZED -> DEPLOYED on evidence URLs only. Nothing below L4 touches
kill_signals. CEO ledger separates known transactions from flagged gaps —
no hallucinated holdings, ever.
