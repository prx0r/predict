# AGENTS.md — bneck2

Binding rules for any coding agent working here. Violate these and the
architecture has failed.

## Absolute rules

1. **NEVER `git push`.** Owner pushes. Commit locally only when asked.
2. **Stdlib only** in `bneck2/` + `collectors/` + `scripts/`. No pip on box;
   no numpy/pandas/networkx/sklearn. Pure functions, JSON in/out.
3. **Collectors never raise.** Fetch fails → `[]`/`{}`/`ok:False` + downstream
   logs INCONCLUSIVE. A dead venue never kills the loop.
4. **Gates dominate objectives.** Kill promotion stays in updater/quant gates;
   diggers below L4 never touch kill verdicts; shorts need the full conjunction.
5. **Missing data → neutral/INSUFFICIENT.** Never bullish, never zero-as-safe,
   never fabricated. Placeholders flagged (`estimated`, `INCONCLUSIVE`).
6. **Receipts immutable.** Prereg amendments are new rows, never edits. Dead
   hypotheses/variables stay listed. n<30 directional-only, labelled.
7. **LLM proposes, code disposes.** No LLM verdicts, no LLM selection
   (mRMR/algorithm prunes), no benchmark-weighted evidence.
8. **No guessed URLs/slugs.** Probe live, log 404s to unknowns, queue them.
9. **Secrets never committed.** Grep audit (`sk-|GOCSPX|ya29|ghp_|password\s*=`)
   before every commit. Keys live in agent-vault, values never printed.
10. **One-table formulas.** Every weight lives in `docs/SYSTEM-SPEC.md` §3 —
    update it with the code or the table lies.

## Commands

```bash
/usr/bin/python3 -m unittest discover -s tests   # 171 tests, keep green
/usr/bin/python3 scripts/status.py --quant --belief
/usr/bin/python3 scripts/migration.py
/usr/bin/python3 -u scripts/oneclick.py          # full loop, writes docs/ONECLICK-*.md
/usr/bin/python3 scripts/experiment.py report
/usr/bin/python3 scripts/killfeed.py --live --max-nodes 3 --no-write  # dry run
```

## Where things are

- Engine `bneck2/` · venues `collectors/` (map: `docs/RESOURCES-CANONICAL.md`,
  limits: `docs/VENUES.md`) · loop `scripts/oneclick.py` (daily cron 06:17 UTC)
- Data `data/` (beliefs/bottlenecks/labs/worlds/universe/backtest) · lab
  `experimentation/` (hypotheses + receipts + variables + predictions)
- Thesis `docs/goated.md` · plan `docs/ML-LAB-PLAN.md` + `CONVERGENCE-PLAN.md`
  · targets `docs/TARGET-90D.md` · endgame `docs/ENDGAME.md`
- Trader recipes `third_party/` (excluded from umbrella) + `docs/TRADERS.md`
- Umbrella `/home/ubuntu/killfeed` → github.com/prx0r/killfeed (public).
  Sync via rsync excludes (.git/third_party/__pycache__/*.db/outbox-separate).

## Open threads (high-signal first)

1. p_market placeholders → pmxt adapter + venue-implied calibration.
2. Backtest n=3 → matures via cron + backfill; significant ~12 dates.
3. Form-4 absolute gates → cadence-relative at baseline n≥10.
4. POWI/TKR/NOVT CIKs (www.sec.gov blocks box); Senate/House (session/PDF).
5. E007/E011 mature on history; optical-attack prediction resolves Sep 20.
6. edgartools ingestion; pmxt; Kelly/fingerprints/vetting (TRADERS.md).
7. api.data.gov key (1 signup flips 4 categories); USPTO/EPO registration.
8. House PTR PDF parsing (needs pdf lib or capitol-api runtime).
9. SemScholar pool (429s); NIH path (405); Lever slugs; 3 lab feeds.
10. Push needs a valid token (remote behind local).
