"""Resolution structurer — title vs conditions, machine-readable.

For each interesting market: fetch full object, segment the resolution
text into requirements / exclusions / timing / source, score structural
complexity (where human/LLM attention goes first), and stage a
valuation record: market_p vs model_p (null until assessed).

Jev's role (see JEV.md): consume this JSON and return model_p +
rationale + key uncertainties. The structurer does the deterministic
part (segmentation, scoring); judgment stays with the agent.

Usage:
    python3 pm/resolution.py --search "Trump renames AI" --out data/resolutions/
    python3 pm/resolution.py --slug trump-renames-ai-by-september-30
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"

REQ_PAT = re.compile(r"\b(must|shall|will resolve to .yes. if|qualifies|requires?|only if)\b", re.I)
EXC_PAT = re.compile(r"\b(does not count|do not count|excludes?|never counts|will not count|unless)\b", re.I)
TIME_PAT = re.compile(r"\b(11:59 PM ET|by [A-Z][a-z]+ \d{1,2},? \d{4}|before \d{4}|December 31,? 202\d|September 30|within \d+ (days|hours))\b")
WEASEL_PAT = re.compile(r"\b(credible|consensus|as determined by|at the discretion|significant|official|reasonable|clearly)\b", re.I)
TEMPORAL_PAT = re.compile(r"\b(regardless of|whether|takes effect|stayed|enjoined|revoked|superseded|within a stated period|comes into (force|effect))\b", re.I)
SOURCE_FALLBACK_PAT = re.compile(r"\b(consensus of|credible reporting|may also be used|however.*may)\b", re.I)


def fetch_search(query: str, limit: int = 5) -> list:
    url = GAMMA + "/public-search?" + urllib.parse.urlencode({"q": query, "limit_tag": limit})
    req = urllib.request.Request(url, headers={"User-Agent": "predict-research"})
    doc = json.load(urllib.request.urlopen(req, timeout=25))
    evs = doc if isinstance(doc, list) else doc.get("events", [])
    out = []
    for ev in evs:
        out.extend(ev.get("markets", [ev]))
    return out


def fetch_slug(slug: str) -> dict | None:
    for prefix in ("/events/slug/", "/markets/slug/"):
        try:
            req = urllib.request.Request(GAMMA + prefix + slug, headers={"User-Agent": "predict-research"})
            return json.load(urllib.request.urlopen(req, timeout=25))
        except Exception:
            continue
    return None


def split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def structure(m: dict) -> dict:
    desc = m.get("description") or ""
    reqs, excs, timing, other = [], [], [], []
    for s in split_sentences(desc):
        if EXC_PAT.search(s):
            excs.append(s)
        elif REQ_PAT.search(s) or TIME_PAT.search(s):
            reqs.append(s)
            timing.extend(TIME_PAT.findall(s))
        else:
            other.append(s)
    try:
        px = json.loads(m.get("outcomePrices") or "[]")
        market_p = round(float(px[0]), 3) if px else None
    except (ValueError, TypeError):
        market_p = None
    weasel = sorted(set(WEASEL_PAT.findall(desc)))
    temporal = sorted(set(TEMPORAL_PAT.findall(desc)))
    source_fallback = bool(SOURCE_FALLBACK_PAT.search(desc))
    complexity = (len(excs) * 2 + len(weasel) * 2
                  + (3 if not (m.get("resolutionSource") or "").strip() else 0)
                  + (2 if len(desc) < 150 else 0))
    # Divergence: how much the conditions move win % away from the
    # title's plain reading. THE ranking criterion. Exclusions carve
    # title-plausible scenarios out; conjunctive requirements narrow;
    # temporal clauses expand-or-shift (revoked-still-counts cuts both
    # ways); source fallback adds a subjective layer under objective text.
    divergence = (len(excs) * 2 + len(reqs) * 1 + len(temporal) * 2
                  + len([t for t in weasel
                         if t.lower() not in ('credible', 'official', 'consensus')]) * 2
                  + (2 if source_fallback else 0))
    return {
        "question": m.get("question"),
        "slug": m.get("slug"),
        "conditionId": m.get("conditionId"),
        # Join key to trentmkelly book ladders (asset_id == clobTokenId).
        # Coverage there is top-100 by volume; thin-book markets won't join.
        "clobTokenIds": m.get("clobTokenIds"),
        "market_p": market_p,
        "bestBid": m.get("bestBid"), "bestAsk": m.get("bestAsk"),
        "spread": m.get("spread"),
        "volume": _num(m.get("volume")), "liquidity": _num(m.get("liquidity")),
        "endDate": m.get("endDate"),
        "umaResolutionStatus": m.get("umaResolutionStatus"),
        "umaBond": m.get("umaBond"), "umaReward": m.get("umaReward"),
        "resolution_source": (m.get("resolutionSource") or "").strip() or None,
        "requirements": reqs,
        "exclusions": excs,
        "timing": sorted(set(t if isinstance(t, str) else t[0] for t in timing)),
        "context": other,
        "weasel_terms": weasel,
        "temporal_clauses": temporal,
        "source_fallback": source_fallback,
        "complexity": complexity,
        "divergence": divergence,
        # Valuation (Jev/agent fills model_p + rationale; null = unassessed).
        "model_p": None, "model_rationale": None, "model_at": None,
        "edge": None,
        "status": "unassessed",
        "structured_at": datetime.now(timezone.utc).isoformat(),
    }


def save(rec: dict, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (rec.get("slug") or rec["question"] or "market").lower()).strip("-")
    p = outdir / f"{slug}.json"
    p.write_text(json.dumps(rec, indent=2))
    return p


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", default=None)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--out", default=str(ROOT / "data" / "resolutions"))
    args = ap.parse_args()
    markets = []
    if args.slug:
        m = fetch_slug(args.slug)
        if m:
            markets = m.get("markets", [m]) if "markets" in m else [m]
    elif args.search:
        markets = fetch_search(args.search)
    else:
        ap.error("need --search or --slug")
    for m in markets:
        rec = structure(m)
        p = save(rec, Path(args.out))
        print(f"[{rec['complexity']}] p={rec['market_p']} req={len(rec['requirements'])} "
              f"exc={len(rec['exclusions'])} weasel={rec['weasel_terms']} :: {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
