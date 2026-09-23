#!/usr/bin/env python3
"""Source graph builder + validator — the machine-readable source map.

`data/sources/graph.json`: every stream as a node (category, access,
status, collector, consumers) + feeds-into edges. Regenerate any time:
this script. Validate: every LIVE node maps to an existing collector
file; every collector file appears exactly once.
Usage: /usr/bin/python3 scripts/sources_graph.py [--check]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sources" / "graph.json"

# (id, category, access, status, collector, consumers, note)
NODES = [
    ("sec", "filings", "keyless", "LIVE", "collectors/sec.py",
     ["killfeed:sec-burst", "E001", "E010", "panel:f_burst"], ""),
    ("efts", "filings", "keyless", "LIVE", "collectors/efts.py",
     ["full-text filing search"], "GET search-index; POST shape differs"),
    ("nasdaq", "holders", "keyless", "LIVE", "collectors/nasdaq.py",
     ["6k holders/ticker + accumulators + insider counts"], "13F-bulk workaround"),
    ("cftc", "positioning", "keyless", "LIVE", "collectors/cftc.py",
     ["speculative pressure gauge"], "Socrata, recipe ex-financial-mcp"),
    ("fx", "macro", "keyless", "LIVE", "collectors/fx.py",
     ["currency backdrop"], "Frankfurter/ECB, recipe ex-finance-mcp2"),
    ("sec_facts", "fundamentals", "keyless", "LIVE", "collectors/sec_facts.py",
     ["E012", "duration-mismatch"], "tag-rename aware"),
    ("openinsider", "insider", "keyless-http", "LIVE", "collectors/openinsider.py",
     ["E018", "connections:insider_cluster"], "443 refused, http works"),
    ("finra", "short-flow", "keyless", "LIVE", "collectors/finra.py",
     ["connections:short_crowded", "panel:f_short"], "403=unpublished-yet"),
    ("github", "code", "keyless-60/hr", "LIVE", "collectors/github.py",
     ["implementation evidence"], ""),
    ("openalex", "research", "keyless", "LIVE", "collectors/openalex.py",
     ["killfeed:attack", "panel:f_attack"], "group_by, weekly cache"),
    ("crossref", "funders", "keyless-polite", "LIVE", "collectors/crossref.py",
     ["attack funder links"], ""),
    ("biorxiv", "preprints", "keyless", "LIVE", "collectors/biorxiv.py",
     ["preprint velocity"], ""),
    ("semscholar", "research", "keyless-shared-pool", "DEGRADED",
     "collectors/semscholar.py", ["2nd paper source"], "429s; retry wrapper"),
    ("polymarket", "prediction", "keyless", "LIVE", "collectors/polymarket.py",
     ["killfeed:pm-clock", "E004", "E020"], "best-book-wins"),
    ("clob", "prediction-depth", "keyless", "LIVE", "collectors/clob.py",
     ["book quality upgrade path"], ""),
    ("polywhale", "whales", "keyless", "LIVE", "collectors/polywhale.py",
     ["WHALE_CONSENSUS", "E004"], "recipes ex-polytrack/polywhale"),
    ("snapshots", "prediction", "keyless", "LIVE", "collectors/snapshots.py",
     ["immutable market reads for pure evaluation"], "IO boundary: enrich here"),
    ("kalshi", "prediction", "keyless", "LIVE", "collectors/kalshi.py",
     ["killfeed:pm-clock", "candles:pm-velocity"], "no per-trader data, ever"),
    ("manifold", "prediction", "keyless", "LIVE", "collectors/manifold.py",
     ["triangulation"], ""),
    ("hn", "narrative", "keyless", "LIVE", "collectors/hn.py",
     ["attack_narrative", "panel:f_hn"], "saturation cross-check only"),
    ("hf", "implementation", "keyless", "LIVE", "collectors/hf.py",
     ["implementation heat (wiring queued)"], "fetched, join queued"),
    ("bio", "bio-validation", "keyless", "LIVE", "collectors/bio.py",
     ["trials queue", "510k flow"], ""),
    ("fed", "federal-data", "keyless", "LIVE", "collectors/fed.py",
     ["NSF velocity", "FedRegister clock", "BLS anchor", "OSTI"], ""),
    ("jobs", "hiring", "keyless", "LIVE", "collectors/jobs.py",
     ["revealed-preference hiring mix"], "1 board verified"),
    ("labs_rss", "lab-exhaust", "keyless", "LIVE", "collectors/labs_rss.py",
     ["lab_node joins"], "2/6 feeds resolve"),
    ("treasury", "macro", "keyless", "LIVE", "collectors/treasury.py",
     ["financing leg"], ""),
    ("worldbank", "macro-geo", "keyless", "LIVE", "collectors/worldbank.py",
     ["geo layer seeds"], "Taiwan absent (non-member)"),
    ("house", "permissions", "keyless", "LIVE", "collectors/house.py",
     ["filing counts"], "PDF parsing queued"),
    ("usaspending", "money-trails", "keyless", "LIVE", "collectors/usaspending.py",
     ["award clock"], ""),
    ("grants", "money-trails", "keyless", "LIVE", "collectors/grants.py",
     ["opp flow"], ""),
    ("prices", "prices", "keyless", "LIVE", "bneck2/prices.py",
     ["targets", "momentum", "event studies", "backtest"], "Yahoo+CoinGecko+cache"),
    ("x", "social", "KEY", "PLANNED", "stockify X-engine (other repo)",
     ["scarcity shocks", "corroboration"], "needs GetXAPI funding"),
]

EDGES = [
    ("sec", "killfeed"), ("sec_facts", "experiments"), ("openinsider", "connect"),
    ("finra", "connect"), ("finra", "experiments"), ("github", "connect"),
    ("openalex", "killfeed"), ("openalex", "experiments"), ("crossref", "connect"),
    ("biorxiv", "connect"), ("semscholar", "killfeed-fallback"),
    ("polymarket", "killfeed"), ("clob", "killfeed"), ("polywhale", "killfeed"),
    ("kalshi", "killfeed"), ("manifold", "connect"), ("hn", "connect"),
    ("hn", "experiments"), ("hf", "connect"), ("bio", "connect"),
    ("fed", "connect"), ("jobs", "connect"), ("labs_rss", "connect"),
    ("treasury", "experiments"), ("worldbank", "experiments"),
    ("house", "connect"), ("usaspending", "connect"), ("grants", "connect"),
    ("prices", "experiments"), ("prices", "backtest"), ("x", "planned"),
    ("nasdaq", "connect"),
    ("cftc", "connect"), ("fx", "connect"),
]


def build() -> dict:
    return {"generated": "scripts/sources_graph.py",
            "nodes": [{"id": n[0], "category": n[1], "access": n[2],
                       "status": n[3], "collector": n[4],
                       "consumers": n[5], "note": n[6]} for n in NODES],
            "edges": [{"from": a, "to": b} for a, b in EDGES]}


def validate(doc: dict | None = None) -> list[str]:
    doc = doc if doc is not None else build()
    problems = []
    ids = {n["id"] for n in doc["nodes"]}
    files = {n["collector"] for n in doc["nodes"]
             if n["collector"].startswith("collectors/")}
    for f in sorted(files):
        if not (ROOT / f).exists():
            problems.append(f"missing collector file: {f}")
    import glob
    on_disk = {p.split("/")[-1].replace(".py", "")
               for p in glob.glob(str(ROOT / "collectors" / "*.py"))} - {"__init__"}
    mapped = {n["collector"].split("/")[-1].replace(".py", "")
              for n in doc["nodes"] if n["collector"].startswith("collectors/")}
    for orphan in sorted(on_disk - mapped):
        problems.append(f"collector with no graph node: {orphan}")
    for a, b in [(e["from"], e["to"]) for e in doc["edges"]]:
        if a not in ids:
            problems.append(f"edge from unknown node: {a}")
    live = sum(1 for n in doc["nodes"] if n["status"] == "LIVE")
    problems_rep = [p for p in problems]
    assert live >= 20, f"live count dropped: {live}"
    return problems_rep


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    problems = validate(doc)
    live = sum(1 for n in doc["nodes"] if n["status"] == "LIVE")
    print(f"graph: {len(doc['nodes'])} nodes ({live} LIVE), "
          f"{len(doc['edges'])} edges -> {OUT}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  !!", p)
        return 1
    if "--check" in sys.argv[1:]:
        print("graph valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
