# Data — historical PM datasets, ranked (researched 2026-09-23)

> Rule: pull selectively, never mirror. Disk has ~25G free. Provenance
> per pull (URL, date, checksum where offered).

## Tier 1 — pull now (free, no key, verified reachable)

| Source | What | Size | Use |
|---|---|---|---|
| trentmkelly/polymarket_historical_data (HF) | 5-min book ladders (side/level/price/size + latency meta), 182 runs/day, fresh today | ~92KB/run | **book history** — the thing that exists nowhere else free |
| CLOB `/prices-history` per token (via `pm-stack` downloader pattern) | daily candles per outcome token | tiny per market | price paths for OUR top-50 → engine backtests |
| Kalshi historical API (`/historical/markets|trades`, candles) | settled markets, trades, OHLC | paginated | Kalshi leg of cross-venue work |
| Kaggle ismetsemedov | 43k events / 100k markets snapshot + CLOB fields, 300MB | one-shot | metadata universe |
| Kaggle implieddata | PM + Manifold 1h OHLCV | small | cross-venue candles |

## Tier 2 — reference or sample (too big to mirror)

| Source | Size | Note |
|---|---|---|
| SII-WANGZJ/Polymarket_data (HF) | 163GB, 1.9B trades | sample via `hf download` file filters only |
| od2961 full-market (HF) | 185GB single snapshots (latest 44.9GB) | resolution-outcome joins; selective only |
| manja316 9.5M prices | free sample; full $9 | cheap if needed |
| LycheeData Kalshi 36GB | pricing unknown | evaluate if Kalshi leg grows |

## Tier 3 — needs user-side keys/accounts

- Kaggle API (account + key) for scripted pulls.
- Kalshi API key for authenticated/historical tiers.
- DepthFeed Pro $29/mo (skip — free tier + our own pulls cover it).
- Tardis paid L2 (skip — trentmkelly covers books free).

## Verdict (2026-09-23, verified live)

**Best for us: trentmkelly selective pulls.** Real 5-min ladders,
~92KB/run, joinable via `clobTokenIds` (now stored on every structured
record). ~17MB/day full coverage — fits easily in 25G free. Pull what
we track, not the all.

Caveats, all verified:
- Coverage is top-100 by volume. Thin-book weird markets (our hunting
  ground) mostly won't be in it — CLOB price-history per token is the
  fallback for those.
- `huggingface_hub` demands auth even for public Xet repos — use
  `curl -L`, which works keyless. No HF token needed.
- Kaggle needs an account (user-side). Nothing pulled from Kaggle yet.
- Full mirrors impossible: SII 163GB + od2961 185GB vs 25G free
  (Documents 33G + Downloads 31G dominate the disk; not touching).
- Disk guardrail: selective pulls only, Parquet-compact, R2 overflow
  if needed.
- trentmkelly depth parquet: 17,592 rows/run, schema
  (market_id, asset_id, outcome, side, level_index, price, size) +
  source latency. Fresh (today).
- Downloader cloned to `/tmp/pmhist/downloader` (amirharati:
  Gamma + CLOB price-history → TSV, resumable, parallel).
