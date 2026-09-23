"""Collectors mutate the graph — the loop-closing (stdlib only).

Every updater is pure: (graph, data, date) -> (graph, mutations).
`run()` binds live/cached feeds. Missing data -> untouched, never neutral.
Evidence appended with provenance; lists capped to keep the file readable.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data" / "bottlenecks" / "graph_v2.json"
EVCAP = 8


def _ev(value: str, source: str, date: str, confidence: float) -> dict:
    return {"value": value, "source": source, "date": date,
            "confidence": confidence}


def _push(obj: dict, ev: dict) -> None:
    evs = obj.setdefault("evidence", [])
    if isinstance(evs, list):
        evs.append(ev)
        del evs[:-EVCAP]


def filings_to_suppliers(graph: dict, cadence: dict[str, dict],
                         date: str) -> tuple[dict, list]:
    """SEC Form-4/deal cadence per ticker -> supplier-link + node evidence.

    cadence[ticker] = {"form4": n30d, "deal": n30d, "base4": median}.
    Burst (>=2x baseline and >=5 filings) is activity, not direction.
    """
    muts = []
    for node in graph.get("nodes", []):
        for sup in node.get("suppliers", []):
            t = sup.get("ticker")
            c = cadence.get(t or "")
            if not c:
                continue
            n4, base = c.get("form4", 0), max(c.get("base4", 0), 1)
            if n4 >= 5 and n4 >= 2 * base:
                ev = _ev(f"{n4} Form-4/30d vs base {base}", "SEC EDGAR",
                         date, 0.6)
                _push(sup, ev)
                _push(node, _ev(f"{t}: {ev['value']}", "SEC EDGAR", date, 0.6))
                muts.append(f"{node['id']}/{t} filing-burst {n4}v{base}")
    return graph, muts


def short_to_crowdedness(graph: dict, short_by_ticker: dict[str, float],
                         date: str) -> tuple[dict, list]:
    """FINRA short-VOLUME share per ticker -> layer/node crowdedness.

    NOTE: feed is daily short-sale volume / total volume (typical ~0.38),
    NOT short interest. Mapping centers the median at 0.5:
    crowdedness = clamp((sv - 0.25) * 3.33, 0, 1).
    Averaged over linked tickers with data; no data -> untouched.
    """
    muts = []
    for node in graph.get("nodes", []):
        vals = [short_by_ticker[t] for sup in node.get("suppliers", [])
                if (t := sup.get("ticker")) in short_by_ticker
                and short_by_ticker[t] is not None]
        if not vals:
            continue
        new = round(min(max((sum(vals) / len(vals) - 0.25) * 3.33, 0.0), 1.0), 3)
        old = node.get("crowdedness")
        node["crowdedness"] = new
        _push(node, _ev(f"crowdedness {old}->{new} from FINRA short-vol "
                        f"avg {sum(vals)/len(vals):.3f} (n={len(vals)})",
                        "FINRA", date, 0.65))
        muts.append(f"{node['id']} crowdedness {old}->{new}")
    return graph, muts


def thirteen_to_suppliers(graph: dict, adds: list[str], drops: list[str],
                          owner: str, date: str) -> tuple[dict, list]:
    """13F adds/drops -> supplier-link evidence on matching tickers."""
    muts = []
    for node in graph.get("nodes", []):
        for sup in node.get("suppliers", []):
            t = sup.get("ticker")
            if t in adds:
                _push(sup, _ev(f"{owner} 13F add", "SEC 13F-HR", date, 0.7))
                muts.append(f"{node['id']}/{t} 13F-add {owner}")
            elif t in drops:
                _push(sup, _ev(f"{owner} 13F exit", "SEC 13F-HR", date, 0.7))
                muts.append(f"{node['id']}/{t} 13F-exit {owner}")
    return graph, muts


def save(graph: dict) -> None:
    GRAPH.write_text(json.dumps(graph, indent=1))


def load() -> dict:
    return json.loads(GRAPH.read_text())


def run(live: bool = True) -> dict:
    """Bind feeds: SEC cadence caches + live FINRA short for linked tickers."""
    import datetime
    today = datetime.date.today().isoformat()
    graph = load()
    tickers = sorted({s.get("ticker") for n in graph.get("nodes", [])
                      for s in n.get("suppliers", []) if s.get("ticker")})
    all_muts: list[str] = []
    # SEC cadence from belief caches (ticker-keyed, no CIK map needed)
    try:
        base = json.loads((ROOT / "data" / "beliefs" / "sec_baselines.json").read_text())
    except OSError:
        base = {}
    cad = {}
    for t, rows in base.items():
        if isinstance(rows, list) and rows:
            last = rows[-1]
            f4 = [r.get("form4", 0) for r in rows if isinstance(r, dict)]
            med = sorted(f4)[len(f4) // 2] if f4 else 0
            cad[t] = {"form4": last.get("form4", 0),
                      "deal": last.get("deal", 0), "base4": med}
    graph, m = filings_to_suppliers(graph, cad, today)
    all_muts += m
    # live FINRA short interest
    if live:
        try:
            import sys
            sys.path.insert(0, str(ROOT))
            from collectors import finra as FIN
            from bneck2 import prices as P
            closes = {c["date"]: 1 for c in P.history("NVDA", "5d").get("closes", [])}
            dates = sorted(closes)[-5:]
            shorts = FIN.short_history([t for t in tickers if "." not in t and "-" not in t][:60], dates)
            last = dates[-1] if dates else None
            if last and last in shorts:
                graph, m = short_to_crowdedness(
                    graph, {t: v for t, v in (shorts[last] or {}).items()}, last)
                all_muts += m
        except Exception as e:
            all_muts.append(f"short-feed skipped: {type(e).__name__}")
    save(graph)
    return {"mutations": all_muts, "n": len(all_muts), "tickers": len(tickers)}
