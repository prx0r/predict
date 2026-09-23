"""SEC companyfacts collector — XBRL fundamentals, keyless ($0).

data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json: every tagged fact
(Revenues, R&D, Assets...). We extract TTM revenue, R&D intensity and
revenue growth — inputs for duration-mismatch (H_tech vs H_valuation)
and consistency arbitrage. Descriptive UA required.
"""
from __future__ import annotations

import json
import urllib.request

UA = {"User-Agent": "bneck research contact@localhost",
      "Accept": "application/json"}


def facts_url(cik: str) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"


REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "SalesRevenueNet")


def _annual(facts: dict, tag: str, form: str = "10-K") -> list[tuple[int, float]]:
    by_fy: dict[int, float] = {}
    for u in facts.get(tag, {}).get("units", {}).get("USD", []):
        try:
            fy = int(u.get("fy", 0))
            v = float(u.get("val", 0))
        except (ValueError, TypeError):
            continue
        if u.get("form") == form and fy > 0:
            by_fy[fy] = v  # last filing for the year wins (amendments)
    return sorted(by_fy.items())


def _revenue_series(gaap: dict, form: str = "10-K") -> list[tuple[int, float]]:
    """Revenue across tag renames (firms switch tags; e.g. Meta 2018).
    Per year, first tag in REVENUE_TAGS order wins."""
    per_tag = {t: dict(_annual(gaap, t, form)) for t in REVENUE_TAGS}
    years = sorted({f for d in per_tag.values() for f in d})
    out = []
    for f in years:
        for t in REVENUE_TAGS:
            if f in per_tag[t]:
                out.append((f, per_tag[t][f]))
                break
    return out


def fundamentals(cik: str, timeout: int = 30) -> dict:
    """{revenues_ttm, rd_intensity, revenue_growth_1y, fyears} or {error}."""
    try:
        req = urllib.request.Request(facts_url(cik), headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:
        return {"cik": cik, "error": str(exc)[:120]}
    gaap = (doc.get("facts", {}).get("us-gaap", {}))
    rev = _revenue_series(gaap)
    rnd = _annual(gaap, "ResearchAndDevelopmentExpense")
    rev_d = dict(rev)
    out = {"cik": cik, "entity": doc.get("entityName", ""),
           "fyears": [f for f, _ in rev]}
    if rev:
        out["revenue_ttm"] = rev[-1][1]
    if len(rev) >= 2 and rev[-2][1]:
        out["revenue_growth_1y"] = round((rev[-1][1] - rev[-2][1]) / abs(rev[-2][1]), 4)
    rnd_d = dict(rnd)
    yrs = [f for f in rev_d if f in rnd_d and rev_d[f]]
    if yrs:
        y = max(yrs)
        out["rd_intensity"] = round(rnd_d[y] / rev_d[y], 4)
        out["rd_year"] = y
    return out
