# HANDOVER — fresh agent start here (2026-09-10 PM UTC)

## Goal
Beat buy-hold with alternative signals (≤3x leverage). Make it legit: real n, train/test discipline, receipts for everything.

## State
- `bneck2/` all green: **224 tests** (`python3 -m unittest discover -s tests`).
- Umbrella `/home/ubuntu/killfeed` → `github.com/prx0r/killfeed` (public).
- Vault: `agent-vault` server `127.0.0.1:14321`, GITHUB_TOKEN in `oracle`.

## Just finished
- **E045 (NVDA alpha, CONFIRMED w/ caps)**: `short_fade` Sharpe 0.82 vs 3x-buy-hold 0.42 on test year, but trails on total return (+22% vs +30%) and 1x-bh Sharpe (0.84). Timing smooths, doesn't add return. `burst_fade` scored 1.24 on test but was ANTI-selected on train — do not claim, paper-trade only.
- **E046 (REFUTED)**: rules don't generalize cross-sectionally.
- **E047 (INCONCLUSIVE, logging)**: `scripts/paper.py` logs NVDA short/burst vs bh daily → `data/paper/nvda.csv` (1 row). Needs cron; resolves at 90 rows.
- **Fish ML review**: their conf>0.8 "62.5%" claim adds nothing over BUY baseline (62.2%); HOLDs auto-labeled wrong. **E048 (REFUTED, n=240)**: de-lookaheaded support-bounce Sharpe -0.65 vs bh +0.87.
- **E049 (preregistered, needs panel)**: monthly factor horse race on HF data, train 2016-20 / test 2021-26.

## In progress — HF 26M-row panel (YOUR FIRST JOB)
- `scripts/hf_panel.py` fetches `paperswithbacktest/Stocks-Daily-Price` via datasets-server `/rows` (sorted by symbol; binary-search blocks, page 100). Stdlib-only, polite (1s gaps, backoff).
- Gotchas learned: server 429s aggressively (parallelism kills it — stay sequential); **background procs get SIGKILLed by the harness — run foreground in ≤40-min chunks**, resume-safe via `.done_*` files; `length=500` probe hung (stay at 100).
- Status: 6/63 symbols cached in `data/hf_panel/daily.jsonl` (AMD COIN CRM NFLX PLTR + INTC partial-reset). 9 `.done_*` were empty-markers — fixed by reset logic already applied.
- Suggested speedup: cache block boundaries to `blocks.json` so resume skips re-search; process universe sorted for locality.

## Next actions (in order)
1. Finish panel fetch (chunks), run `python3 scripts/hf_horserace.py`, then `python3 scripts/experiment.py run E049`.
2. Wire E049 into `tests/test_migration.py` ID list + `docs/SYSTEM-SPEC.md` §3 row (one-table-formulas rule).
3. Add `scripts/paper.py` to cron alongside `oneclick.py` (06:17 UTC).
4. If E049 refutes: next legit shots are (a) PM-convergence features on the monthly panel, (b) short-side timing in chop (timing earns in chop, not melt-ups), (c) HF panel → cross-sectional ML per `docs/ML-LAB-PLAN.md`.
5. Rotate the `ghp_` token pasted in chat history (in shell + chat logs; vault copy works until rotated).

## Rules that bite
- Stdlib only in `bneck2/`+`collectors/`+`scripts/`; collectors never raise; receipts immutable; missing→INCONCLUSIVE; secrets grep before commit (`scripts/check_secrets.sh`); weights live in `docs/SYSTEM-SPEC.md` §3.
-Sync: rsync excludes (.git/third_party/__pycache__/*.db/outbox-separate) then commit umbrella; owner pushes (or push only when explicitly told).
