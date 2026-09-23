# Handover — next agent (bneck2/killfeed, from 2026-09-10)

## 0. First commands

```bash
cd /home/ubuntu/bneck2
/usr/bin/python3 -m unittest discover -s tests   # expect 161/161
/usr/bin/python3 scripts/status.py --quant --belief
/usr/bin/python3 scripts/migration.py
/usr/bin/python3 -u scripts/oneclick.py          # full loop (~4 min)
/usr/bin/python3 scripts/experiment.py report
```

No pip on this box — stdlib only. stockify needs `uv sync` elsewhere.
Never `git push` (owner pushes). Never commit secrets (grep audit first).

## 1. Layout (what lives where)

- `bneck2/` — engine: graph, quant, belief, updater, worlds, labs, diggers,
  patents, ceo, scarcity, killfeed, backtest, implied, obsolescence,
  migration, consistency, atoms, connect, lab, experiments, prices,
  kernel_bridge. Formulas: `docs/SYSTEM-SPEC.md` §3 (update it with code).
- `collectors/` — 20 venues (see `docs/RESOURCES-CANONICAL.md` for live map,
  `docs/VENUES.md` for PM/Kalshi limits).
- `data/` — beliefs (claims, kill_observations.jsonl, signals.jsonl,
  unknowns.json, sec_baselines.json), bottlenecks (graph_v2, severity
  history, readings), labs, worlds, universe, backtest/panel.jsonl,
  levin? NO — Levin corpus lives in stockify (`~/stockify/data/levin/`).
- `scripts/` — poll, status, revealed, killfeed, seed_claims, migration,
  experiment, oneclick, import_pack, stage_zip, send_gmail.
- `experimentation/` — hypotheses + receipts.jsonl + notes (cg-flow, see
  `third_party/cg` SPEC). `docs/goated.md` = master thesis.
- `third_party/` — clones (excluded from umbrella). Trader verdicts:
  `docs/TRADERS.md`. `pmxt`, `pm-analysis` present.
- `imports/` — pristine zips. `outbox/` — fresh stage zip.
- Umbrella `/home/ubuntu/killfeed` → github.com/prx0r/killfeed (public).
  Sync: rsync (excl .git/third_party/__pycache__/*.db/outbox→separate).
  Remote is 1 commit behind (41cb458 needs push with valid token).
- Stale: `/home/ubuntu/stale/` (README explains each). Old ONECLICK
  reports: `docs/archive/`.
- Cron: daily 06:17 UTC oneclick → `data/oneclick-cron.log`. Linger on.

## 2. Credentials (locations, never values)

- Agent vault: `127.0.0.1:14321`, owner session on disk, unattended token
  `~/.agent-vault-opencode-token` (proxy role: NO credential reads).
  Owner session CAN read (admin). Oracle vault: 43 keys + main HF_TOKEN.
- Known-dead: vaulted GITHUB_TOKEN (401), two pasted PATs (401). Push needs
  a fresh classic PAT (repo scope). Secrets previously scrubbed from tree;
  rotate Google OAuth + sk-A5Q… if ever exposed (history rewritten pre-push,
  but assume compromised).

## 3. Live state (what the data says right now)

- Triggers holding: NVDA SEC burst (Stevens $411M + $1.09B 144), optical
  SEC burst + OpenAlex attack (+130%).
- dB/dt compounding (3+ pts/node); backtest panel 13 scores, INSUFFICIENT
  until forwards mature (~days). Baselines seeded (5 tickers).
- Open unknowns: POWI/TKR/NOVT CIKs (www.sec.gov blocks box), Senate PTR
  (403), NIH path (405), SemScholar pool (429s), Lever slugs, 4 lab feeds.

## 4. Future dev steps (ordered)

**P0 — no deps, this box:**
1. Push umbrella (valid token): `cd ~/killfeed && git push`.
2. Free `api.data.gov` key → wire Congress/GovInfo/Regulations/EIA (user signup).
3. Keep daily cron green; watch `data/oneclick-cron.log`.
4. Resolve POWI/TKR/NOVT CIKs (alt source: not www.sec.gov), Senate/House paths.
5. PM query re-probe ( Tunables: `PM_QUERY_OVERRIDES`); Kalshi thin — series-targeted queries.
6. Curate `arb_pairs.yaml`-equivalent: human-confirmed PM↔Kalshi pairs (E008).
7. Form-4 absolute→cadence-relative gates once baselines hit n≥10.

**P1 — needs deps/box (`uv`, pandas, npm):**
8. stockify green + feeds consume engine Signal (`ranking.py`).
9. pmxt adapter → venue-implied p_market (kills placeholders; sharpens consistency).
10. Backtest-vet whale leaders; Kelly sizing; algo-fingerprints (TRADERS.md recipes).
11. edgartools filing ingestion (backlog/language diffs).
12. TechToken/convergence/patentomics (embeddings+GPU).

**P2 — needs history/gating:**
13. 90-day briefs → backtest significance → paper portfolio vs baselines.
14. Usage telemetry, actor graph, reverse-DCF, geo layer (goated §§15,19,31,37).
15. Postgres + backups + hardening. NO capital/executors before 13 is green.

## 5. House rules (from cg AGENTS + hard lessons)

- Receipts canonical; projections rebuildable. Falsifier or vibe.
- n<30 directional-only, labelled. Never average roles/clocks together.
- Missing data → neutral/INSUFFICIENT, never bullish, never zero-as-safe.
- Collectors never raise; killfeed skips + logs INCONCLUSIVE.
- One-table formulas (SYSTEM-SPEC §3). Tests for every mechanism.
- No guessing URLs/slugs — probe, log 404s, queue them.
