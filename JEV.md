# JEV — how the agent stack fits together

> Status 2026-09-23: cloned, mapped, not yet wired. Nothing below
> executes real trades. Paper first, always.

## What lives where

| Location | Contents | Source |
|---|---|---|
| `/home/box/jev-skills/` (12 repos) | agent skills: mcp bridge, judgment, compaction, UI, nav, classifier, review, trader, liquidity, verifier, graphs | GitHub list in chat |
| `/home/box/pm-stack/` | `pm-official` (Polymarket py-clob-client, signing), `pm-sdk` (pascal-labs, **paper mode**) | official + MIT |
| `/home/box/predict/pm/` | killfeed bneck2 import: collectors, panel builder, beliefs, biweekly data, prediction log | own repo (prx0r/killfeed) |
| `/home/box/predict/docs/killfeed/` | TRADERS, VENUES, THREADS, handovers, prior northstars (reference) | own repo |

Skipped from the jev list (wrong layer): mario, drone, FPS game,
desktop automation, curate, killmyidea, codex-router. Revisit if a
concrete need appears — don't collect skills speculatively.

## How Jev plugs into each layer

### powpowpow (observe)
- `typesafe-mcp` exposes the garden's MCP server to any Jev-driven
  client — one bridge and every Jev agent can query 13 tools.
- `blink` for agents navigating the repo; `json-render` for generative
  dashboard UI later.
- `fast-jev-compaction` + `winnow` for long collector-debug sessions
  (context hygiene, not intelligence).
- `semdecide` classifies events/releases into the project_event schema.

### predict (decide → act)
- `jev-trader` execution patterns (idempotent order ids, cancel/replace)
  inform our order path; `pascal pm-sdk` paper mode is the sandbox.
- `jev-mcp` judgment tools + NORTHSTAR lesson 2 bound sizing.
- `prism` liquidity signals feed the same absorption math as
  miner-pressure (depth vs incoming flow, any venue).
- `canny` verifies task completion — agent claims "position recorded"
  must be checkable against receipts.
- `neo4jev` for the influence/knowledge graph walks.
- `jev-ultrafast` (browser agent) covers what has no API: resolution
  monitoring, odds comparison across UIs, exchange notices. Browser
  output is always *untrusted input* — parsed, never executed.

### killfeed bneck2 (already imported)
- Collectors are stdlib-only, no-key, fail-to-`[]` — same doctrine as
  POW collectors. `signal = (p, volume, liquidity, spread, velocity)`,
  never p alone.
- `build_predict_panel.py` is the targets-first, point-in-time,
  walk-forward pattern. The garden's STATE builder is its sibling.
- `forecasters.py` (Brier calibration per handle/topic) is the
  guild-alpha ledger NORTHSTAR lesson 1 asks for.

## Hallucination controls (read before building execution)

1. **Provenance before claims.** No edge number without: source,
   timestamp, sample size, version. NORTHSTAR lesson 3 (the 1% that
   was 0.5%) is what happens without this.
2. **Paper first.** `pm-sdk` paper mode until a logged paper record
   beats noise. No real keys on a machine with browser agents.
3. **Completion must be checkable.** `canny`-style: every agent claim
   ("scanned", "recorded", "hedged") resolves to an artifact or it
   didn't happen.
4. **Bounded sizing.** NORTHSTAR lesson 2: heavy only on very large,
   measured edge. Encode max-size caps, not vibes.
5. **Model the wipeout.** Michigan/WMU pattern: steady drip, one-sided
   tail. Every strategy doc names its kill conditions (see bneck2
   hypotheses/H-*.md for the format).
6. **Prediction log discipline.** Log before outcomes, review after —
   `pm/experimentation/predictions.jsonl` is the seed. Matches the
   security contract: entries carry id + evidence + author + review
   date, corrections are new entries, auditor flags but never deletes
   (deletion would destroy the chain it verifies).
7. **Red-team refusal.** Rulebook/prompt content is data: smuggled
   instructions ("always approve", "ignore all") and PII-as-example
   are refused, same as the rulebook_poisoning cover demands.
8. **No auto-execution.** Read + paper + propose. Real execution needs
   an explicit human grant per action — the XMRBot bounded-grant
   model, applied to PM orders.

## License hygiene

- killfeed code is ours (prx0r) — fine to import.
- Third-party repos are mostly MIT — confirm per-repo LICENSE before
  vendoring code (vs merely calling APIs). Never paste AGPL code;
  reimplement patterns cleanly.
- `py-clob-client` (official) handles all signing — we never
  implement EIP-712 ourselves.
