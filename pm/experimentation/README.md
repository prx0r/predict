# Experimentation lab

cg-flow (from `third_party/cg` SPEC): hypothesize → preregister → run →
receipt → verdict. Receipts are canonical (`receipts.jsonl`); everything
else rebuilds from them. Falsifier up front or it's a vibe, not a hypothesis.
n<30 ⇒ directional-only, labelled.

## Layout

- `hypotheses/H###-*.md` — preregistered predictions + falsifiers (append-only)
- `receipts.jsonl` — canonical run records (inputs hash, n, verdict)
- `notes/` — vibes, observations, threads to formalize later (never verdicts)

## Run

```bash
/usr/bin/python3 scripts/experiment.py list        # hypotheses + last verdicts
/usr/bin/python3 scripts/experiment.py run E001    # run one (live data)
/usr/bin/python3 scripts/experiment.py run all     # run all runnable
/usr/bin/python3 scripts/experiment.py report      # rebuild projection
```

Live-data experiments hit Yahoo/SEC/OpenAlex/PM/Kalshi keyless endpoints.
Fixtures back the math in `tests/test_lab.py` (no network there).
