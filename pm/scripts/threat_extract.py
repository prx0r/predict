"""Death-watch extractor — researcher threat intel -> THREATENS overlay.

Mines feedify researcher corpora for (researcher -> company -> negative
impact) triples: structured "Affected companies (TICK: US) — impact" read-
throughs plus $TICKER/threat-word proximity. ProphetMap moatCapture<=1 adds
structural flags. Output: data/bottlenecks/threats.json (ranked) and
threat_graph.json (CO_ company nodes + THREATENS edges — overlay file, kept
separate from the physical production graph). Stdlib only.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "third_party" / "feedify" / "data" / "raw"
PRIMA = ROOT / "third_party" / "feedify" / "august" / "prima_materia"
OUT = ROOT / "data" / "bottlenecks" / "threats.json"
OVERLAY = ROOT / "data" / "bottlenecks" / "threat_graph.json"

READTHRU = re.compile(
    r"([A-Z][A-Za-z0-9 .,&'\-]+?)\s*\(([A-Z]{1,5}):\s*US\)\s*[—–\-–]\s*"
    r"(positive|negative|mixed[^;.\n]{0,80})", re.IGNORECASE)
TICK = re.compile(r"\$([A-Z]{1,5})\b")
THREAT = re.compile(r"negativ|short|obsolet|disrupt|threat|replac|commodit|"
                    r"deflat|kill|die\b|dying|undercut|disintermediat|"
                    r"margin compress|pricing power (loss|erod)|structurally "
                    r"(challeng|worse|negative)|headwind", re.IGNORECASE)


def _tweets(path: Path):
    try:
        d = json.loads(path.read_text())
    except Exception:
        return
    items = d if isinstance(d, list) else d.get("tweets", d.get("data", []))
    for it in items:
        if isinstance(it, dict) and it.get("text"):
            yield it.get("text", ""), str(it.get("created_at", it.get("date", "")))[:10]


def extract() -> dict:
    threats: dict[str, dict] = defaultdict(
        lambda: {"researchers": set(), "negatives": 0, "positives": 0,
                 "quotes": []})
    files = (list(RAW.glob("*.json")) if RAW.exists() else [])
    if PRIMA.exists():
        files += list(PRIMA.glob("*.json"))
    for f in files:
        researcher = f.stem.replace("_august2026", "").lstrip("@")
        for text, date in _tweets(f):
            for m in READTHRU.finditer(text):
                company, tick, impact = m.group(1).strip(), m.group(2).upper(), m.group(3)
                t = threats[tick]
                t["researchers"].add(researcher)
                if impact.lower().startswith("neg"):
                    t["negatives"] += 1
                    t["quotes"].append({"by": researcher, "date": date,
                                        "text": f"{company}: {impact.strip()}"[:200]})
                else:
                    t["positives"] += 1
            if THREAT.search(text):
                for tm in TICK.finditer(text):
                    seg = text[max(tm.start() - 150, 0):tm.end() + 150]
                    if THREAT.search(seg):
                        tick = tm.group(1)
                        t = threats[tick]
                        t["researchers"].add(researcher)
                        t["negatives"] += 1
                        if len(t["quotes"]) < 3:
                            t["quotes"].append(
                                {"by": researcher, "date": date,
                                 "text": " ".join(seg.split())[:200]})
    # ProphetMap structural flags
    try:
        uni = json.loads((ROOT / "third_party" / "prophetmap" / "data" / "universe.json").read_text())
        us = uni if isinstance(uni, list) else uni.get("tickers", [])
        for u in us:
            try:
                if u.get("moatCapture") is not None and int(u["moatCapture"]) <= 1 and u.get("symbol"):
                    t = threats[u["symbol"]]
                    t["moat_flag"] = u.get("moatFalsification", "")[:200]
            except (ValueError, TypeError):
                pass
    except OSError:
        pass
    out = {}
    for tick, t in threats.items():
        if t["negatives"] == 0 and "moat_flag" not in t:
            continue
        out[tick] = {"researchers": sorted(t["researchers"])[:8],
                     "n_researchers": len(t["researchers"]),
                     "negatives": t["negatives"], "positives": t["positives"],
                     "quotes": t["quotes"][:3]}
        if "moat_flag" in t:
            out[tick]["moat_flag"] = t["moat_flag"]
    return dict(sorted(out.items(), key=lambda x: (-x[1]["negatives"], x[0])))


def build_overlay(threats: dict, min_neg: int = 2) -> dict:
    nodes, edges = [], []
    for tick, t in threats.items():
        if t["negatives"] < min_neg or not t["quotes"]:
            continue
        nodes.append({"id": f"CO_{tick}", "type": "company", "label": tick,
                      "status": "watched", "grade": "SUPPORTED",
                      "provenance": "feedify researcher corpus"})
        seen, ev = set(), []
        for q in t["quotes"]:
            if q["text"] in seen:
                continue
            seen.add(q["text"])
            ev.append({"value": q["text"], "source": f"feedify:{q['by']}",
                       "date": q["date"] or "2026-08", "confidence": 0.55})
            if len(ev) >= 3:
                break
        if t.get("moat_flag"):
            ev.append({"value": t["moat_flag"], "source": "prophetmap moat",
                       "date": "2026-09-10", "confidence": 0.5})
        edges.append({"source": "PML_L0", "target": f"CO_{tick}",
                      "relation": "THREATENS", "grade": "SUPPORTED",
                      "valid_from": "2026-08-01", "valid_to": None,
                      "confidence": "medium",
                      "requirement": {"quantity_per_unit": None, "unit": None, "confidence": None},
                      "supply": {"global_capacity": None, "utilization": None,
                                 "lead_time_months": None, "capacity_growth_rate": None},
                      "substitution": {"alternatives": [], "score": None},
                      "timing": {"needed_by": None, "capacity_available_by": None},
                      "evidence": ev,
                      "note": "AI model/app capability threatens cash flow (researcher-sourced)"})
    return {"nodes": nodes, "edges": edges}


def main() -> dict:
    threats = extract()
    OUT.write_text(json.dumps(threats, indent=1))
    overlay = build_overlay(threats)
    OVERLAY.write_text(json.dumps(overlay, indent=1))
    top = list(threats)[:10]
    return {"tickers": len(threats), "overlay_nodes": len(overlay["nodes"]),
            "overlay_edges": len(overlay["edges"]), "top": top}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
