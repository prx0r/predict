"""World Bank collector — macro/geo indicators, keyless ($0).

api.worldbank.org/v2: GDP, energy, R&D, high-tech exports per country.
Feeds the geo layer (goated §31): energy/land/capability differ by place.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://api.worldbank.org/v2"
UA = {"User-Agent": "bneck"}

INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",
    "rd_gdp": "GB.XPD.RSDV.GD.ZS",
    "hitech_exports": "TX.VAL.TECH.MF.ZS",
    "electric_access": "EG.ELC.ACCS.ZS",
    "industry_va": "NV.IND.TOTL.ZS",
}


def indicator(country: str, code: str, years: str = "2020:2025",
              timeout: int = 25) -> list[dict]:
    ind = INDICATORS.get(code, code)
    try:
        url = (f"{API}/country/{urllib.parse.quote(country)}/indicator/{ind}"
               f"?format=json&date={years}&per_page=10")
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        rows = doc[1] if isinstance(doc, list) and len(doc) > 1 else []
        return [{"country": country, "indicator": code, "date": x.get("date"),
                 "value": x.get("value")} for x in rows if x.get("value") is not None]
    except Exception:
        return []
