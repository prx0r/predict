# Process — resolution sweep 2026-09-23

> How 1677 markets became 50 structured records. Every choice below is
> logged so the next sweep doesn't re-learn it.

## Pipeline (`pm/sweep_resolutions.py`)

1. **Gather.** 33 queries (politics, sports, crypto, tech, culture,
   weather, economy, world) × Gamma `public-search` limit 10.
   Raw yield varies wildly per query (Olympics returned 99 —
   `limit_tag` is advisory, not enforced).
2. **Dedupe** by `conditionId` → **1677 unique** (queries overlap heavily).
3. **Structure all** via `pm/resolution.py` (requirements / exclusions /
   timing / source / book snapshot).
4. **Rank** → top 50 JSONs + `_sweep_stats.json`.

## Scoring, v1 → v2 (the day's main lesson)

- **v1:** exclusions×2 + weasel×2 + missing-source+3 + thin-text+2.
  Result: `credible`/`official`/`consensus` hit ~50/54 records — they
  are UMA template boilerplate, not signal. v1 ranked template
  compliance, not ambiguity.
- **v2:** template terms subtracted; score = exclusions×2 +
  non-template-weasel×2. AI-rename still top (4 real exclusions);
  volume leaders (ceasefire Dec $2.6M, Taiwan clash $3.4M) correctly
  score ~0 — clean texts the market prices confidently.
- **Missing `resolutionSource`: dead signal.** Empty on 54/54 — the
  field is just never populated on Gamma. Removed from scoring;
  still recorded.
- Priority for the top-50 cut: `complexity × (1 + log10(volume+1))`
  + live bonus. Complexity finds lawyers; volume finds anyone-cares.

## Findings (verified live)

1. **AI-rename (c=8 v2):** 4 exclusions doing real work (social posts,
   office renames, product renames, incidental use all carved out).
   p=0.235, 7 days left. Top watch item.
2. **Taiwan blockade (c=4):** "announces OR de facto establishes" +
   single-seizure carve-out "unless part of an enforced pattern" —
   the gray zone is what counts as a *pattern*. p=0.038, $371k.
3. **Nobel Trump/Machado ($1.9M, resolved):** "no official confirmation
   needed" + "clearly demonstrating agreement" — the template for
   future joint-prize markets. Study, don't trade (resolved).
4. **Putin-meet set sums 1.017** (separate check): over-dollar basket,
   needs live-book verification.
5. **Hurricane set sums 0.986**: complete 4-bucket set, thin books.

## Failure log (so we don't repeat)

- `volume` arrives as **string** on some Gamma rows → TypeError in
  ranking. Fixed: `_num()` normalization in `resolution.py`.
- `pgrep -f sweep_resolutions` **self-matches** — "STILL RUNNING"
  readings were phantom. Use `[s]` bracket trick.
- Gamma `limit_tag` unenforced (Olympics: 99 rows for limit 10).
  Dedupe by conditionId handles it; don't assume 10/query.
- Search ranking favors resolved markets (2023 NFL, 2025 Oscars).
  Always filter `endDate >= today` + exclude p∈{0,1} before analysis.
