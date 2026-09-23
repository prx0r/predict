# NORTHSTAR-4 — tournament loop (the northstar)

Supersedes the *process*, not the thesis (goated.md still says what;
NORTHSTAR-2/3 say how it's measured). This doc says how the work
organizes itself forever: hypotheses enter as seeds, face data in
rounds, mutate with logged justifications, and either promote or die.
The agent's job is running rounds until the stop criterion fires —
then peer review takes over.

## 1. Objects

- **Seed set** (`data/tournament/<round>/seeds.json`): the competing
  hypotheses/variables/factors this round, each with parent IDs +
  justification for any mutation from the prior round.
- **Round** (`data/tournament/<round>/`): `seeds.json` in,
  `results.json` + receipts out. Deterministic given data snapshot.
- **Branches**: each round is a git branch `tournament/<round>` in the
  umbrella (code+data state reproducible; merge nothing — branches ARE
  the record).
- **a-log**: every A-task action appended (`experimentation/a-logs/`).
- **a-report**: per-A-task validation evidence (`experimentation/a-reports/`
  `<task>.md`: claim → evidence → verdict). Peer review reads these.

## 2. Round protocol

1. **Enter**: seeds = survivors + bandit proposals (with arm + justification).
2. **Screen**: identical screens for all seeds (IC/hit-rate/Wilson, same
   panel, same splits). No hand-tuning per seed.
3. **Promote/demote**: clear bar → advance; miss → dead list (kept).
4. **Mutate**: refine borderline (new ID, parent noted), drop losers,
   each change justified in `mutations.json` (why, citing receipt).
5. **Rerun**: seed1.1 faces fresh holdout (never the data that seeded it).
6. **Stop check**: a-log↔a-task match — every planned A-task has a
   validation-evidence a-report. Unmatched tasks = keep working.

## 3. Stop criterion (when the agent stops)

ALL of: every A-task has an a-report; every a-report cites validation
evidence (receipt IDs, not prose); suite green; threads --check green;
no open thread is both high-priority and autonomous-runnable. Then output
for peer review, which hunts hallucinations and sends back tasks.

## 4. Peer-review handoff format

Per A-task: claim, evidence (receipt/log/doc links + hashes), verdict,
known gaps. Reviewer verdicts: ACCEPT / CHALLENGE (with counter-evidence)
 / SEND-BACK (new A-task spawned). Nothing merges to mainline narrative
 without ACCEPT.
