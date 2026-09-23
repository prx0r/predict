# Resolutions — the dispute surface (researched 2026-09-23)

> Thesis: thin markets aren't priced wrong most often — they're
> *worded* vaguely. Resolution text is the attack surface. All fields
> below come keyless from the Gamma API (`description`,
> `resolutionSource`, `umaBond`, `umaReward`, `umaResolutionStatus`).

## Mechanics (official docs, verified)

- Anyone proposes an outcome + posts bond (typically $750 pUSD).
- **2-hour challenge window.** Undisputed → proposer gets bond back + reward.
- Disputed → new round; double-disputed → UMA DVM token-holder vote (~48h + 24–48h debate).
- Disputer wins → bond back + **half the proposer's bond**. Proposer wins → mirror.
- `Too Early` and `Unknown/50-50` exist as outcomes; P50 splits both sides.
- Crowdfunded dispute pools exist (polydispute.finance) — bond costs split pro-rata.

## Prior art (cloned to /home/box/pm-stack/)

| Repo | What | Status |
|---|---|---|
| `pm-dispute-bot` (sigma-quantiphi) | polls `uma_resolution_status=proposed`, disputes when midpoint disagrees >20¢, **dry-run by default** (`LIVE=1` to fire) | pattern reference |
| `pm-disputes` (chapmansgit) | pulls ALL historical UMA disputes (Gamma + UMA subgraph fallback, ~558 events) | historical dataset builder |
| `pm-dispute-alerts` (genkisudo) | wallet-flip alerts (YES→NO/NO→YES), skips sports/crypto/weather | flow-watch pattern |

## Live findings (2026-09-23, verified via Gamma)

1. **No live disputes right now.** Sampled hurricane, election, Fed,
   BTC, temperature sets — zero `umaResolutionStatus` in
   proposed/disputed state. The monitor's job is catching the next one
   inside its 2-hour window.
2. **Empty `resolutionSource` is pervasive** — nearly every market.
   Not a flag by itself; the signal is in `description` text quality.
   Vagueness scoring (weasel-word rank) is the follow-up build.
3. **Atlantic hurricanes 2026 (single event, 4 buckets): sum ≈ 0.986**
   on last-trade (0.365 / 0.575 / 0.039 / 0.007). Complete set, shared
   794-char resolution text, thin books ($1–1.5k). Textbook watchlist
   shape — verify against live books before any conclusion; ~0.5c net
   after fees IF fills hold. NOT a trade, a monitor seed.
4. **Trump-endorses-Israeli-party set**: many 0.001 legs + "not endorse"
   0.445 — same set-sum structure, check completeness before math.

## Monitor design (next build)

- 5-min poll: markets with live UMA proposals + set-sum drift on
  tracked exclusive sets + empty-source new listings.
- Alert on: any `proposed`/`disputed` status; set-sum past 0.985/1.015
  on live books (not last-trade); new markets with missing source.
- Paper log only. Disputing costs $750 a pop — no auto-disputes, ever.
