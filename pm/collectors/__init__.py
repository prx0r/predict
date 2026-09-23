"""bneck collectors — starter free-source collectors. Stdlib only.

Each module: build_*() URL constructors + parse_*() pure parsers (tested
offline with fixtures) + fetch_*() thin network wrappers that return []
on any failure (rate limits, no key, offline). No keys needed except
optional GitHub token (raises rate limit 60 -> 5000/hr).

Collectors: sec (EDGAR), github (repo events), openalex (attack velocity),
polymarket (Gamma search), usaspending (awards), grants (grants.gov).
"""
