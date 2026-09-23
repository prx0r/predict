# Prediction-market venues — API map, limits, what's possible (2026-09-10)

Sources: https://docs.kalshi.com/llms.txt, https://docs.polymarket.com/llms.txt
(fetched 2026-09-10). We use keyless public market-data endpoints only.
No trading, no portfolio, no WebSocket — those need keys/plans we don't have.

## Kalshi — `https://api.elections.kalshi.com/trade-api/v2`

Despite the subdomain, production Trade API covers ALL markets, not just
elections. No key needed for market data.

What we use (`collectors/kalshi.py`):
- `GET /events?status=open&with_nested_markets=true&limit=200` (+cursor,
  max 200/page, capped at 3 pages) → keyword-match titles client-side
  (no full-text search param exists).
- Price: `last_price_dollars`, else mid of `yes_bid/ask_dollars`.
  Volume: `volume_24h_fp` else `volume_fp`. Liquidity: `liquidity_dollars`.
- Tiers reuse the Polymarket thresholds for cross-venue comparability.

Rate limits (token bucket, per docs/getting_started/rate_limits):
- Basic Read 200 tokens/s, Write 100/s; default cost 10 tokens → ~20 reads/s
  sustained on the free tier. 429 = `{"error":"too many requests"}`, NO
  Retry-After headers → exponential backoff, no penalty/cooldown.
- Our usage (~50 reads/pass, ~1/s) is ~5% of Basic. No key needed at
  this volume. Higher tiers (Advanced 300 … Prestige 10000) need account
  + volume; check grants via `GET /account/limits` (key required).

Price history (wired 2026-09-10): `GET /series/{series}/markets/{ticker}/candlesticks`
(1/60/1440-min OHLC + volume/OI; settled pre-cutoff via /historical). Gives pm price
velocity per market — feed into dB/dt-style pm momentum next.

Possible next (all keyless): `GET /markets` (series_ticker/status filters),
per-market orderbook (`/markets/{ticker}/orderbook` — bids only, binary
structure), candlesticks (1m/1h/1d), all-trades feed, series list
(`tech` discovery instead of keyword match), event forecast history,
historical markets/trades (pre-cutoff), multivariate events, live-data
milestones (weather/crypto indexes). WebSocket + trading need RSA keys.

Maintenance: exchange pauses scheduled; `GET /exchange/status` tells.

## Polymarket — `https://gamma-api.polymarket.com`

All market-data endpoints below are public, no key. Trading (CLOB) needs
wallets/session keys — out of scope.

What we use (`collectors/polymarket.py`):
- `GET /public-search?q=…&limit_tag=…` → events → markets → outcomePrices[0].
  Volume/liquidity as returned; same tier fn as Kalshi.
- Raw price = first outcome price; resolved markets read 0.0/1.0 (handled:
  best-book prefers liquidity, resolved books are usually thin).

Rate limits: Gamma public reads are "Standard" unpublished bucket on the
Unverified tier; builder tiers (Verified/Partner) raise CLOB/relayer limits
(100 → 10k relay txns/day), not public reads. Our ~16 reads/pass is noise.
If Gamma ever 429s, back off the same way (no documented Retry-After).

Possible next (all keyless): keyset pagination (`/events/keyset`,
`/markets/keyset?tag_id=…&closed=false`, `after_cursor`) for full-universe
sweeps instead of per-query search; tag graph (`/tags`, related-tags) for
topic expansion; series/sports metadata; market details + CLOB orderbooks
via clobTokenIds; public analytics; RTDS realtime feeds; Chainlink TWAPs.
Keyset sweep would let us score EVERY market once per pass and match
locally — strictly better than 16 searches when we outgrow them.

## Venue comparison for the pm clock

| | Polymarket | Kalshi |
|---|---|---|
| Search | `public-search?q` server-side | none — page + match locally |
| Pagination | keyset cursors | cursor, 200/page |
| Price | outcomePrices[0] | last_price else yes mid |
| Liquidity signal | volume/liquidity fields | liquidity_dollars + OI |
| Orderbook | CLOB via token ids (next) | per-market bids (next) |
| Resolved markets | 0.0/1.0 prices linger | status filter available |
| Limits @ our volume | ~0% of bucket | ~5% of Basic |
| Auth needed | only to trade | only to trade/higher tiers |

Rule (unchanged): best book across venues wins; p never travels without
tier + venue + reliability. Thin books stay coin-flips.
