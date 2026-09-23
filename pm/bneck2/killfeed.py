"""bneck2 killfeed — collectors -> verdict writers (build-queue #1-3).

IO BOUNDARY (peer-review P0 fix, enforced by tests/test_purity.py):
  - run() and collectors/* do ALL network I/O.
  - evaluate(), pm_reading(), sec_burst(), attack_intensity() are PURE:
    no imports of collectors, no sockets, no files. They take fetched
    docs and MarketSnapshots (collectors/snapshots.py) and return rows.
  - write_rows() does ALL disk writes.
Evaluation with sockets disabled must succeed on fixtures.

Design rules (do not weaken):
  - Collectors never raise (return [] / {}); killfeed skips missing inputs
    and logs INCONCLUSIVE rather than inventing data.
  - Nothing below digger L4 touches kill verdicts — this module writes
    *observations* (TRIGGERED / NOT TRIGGERED / INCONCLUSIVE). Promotion to
    kill_signals stays in updater/quant gates.
  - SEC UA must stay descriptive (data.sec.gov blocks contact@localhost-style
    anonymity; see collectors/sec.py UA).

Thresholds live in THRESHOLDS (one place, auditable).
Venue reliability lives in calibration.pm_reliability (single epistemology).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from bneck2 import calibration as CAL
from bneck2 import evidence as E
from bneck2 import graph as G

BASELINES_PATH = ROOT / "data" / "beliefs" / "sec_baselines.json"
BASELINE_KEEP = 30

# accession ledger: which SEC filings have already been counted, per CIK.
# Peer-review P0 fix: the unit of evidence is the accession number, so a
# poll can never re-count the same filing. (File lives in data/beliefs/.)
SEEN_PATH = ROOT / "data" / "beliefs" / "sec_seen.json"

THRESHOLDS = {
    # SEC burst: NEW filings since last poll (accession-deduped).
    "sec_form4_burst": 5,     # >=5 new insider Form 4s
    "sec_deal_burst": 2,      # >=2 new 8-K / 13D / 13G
    # OpenAlex attack intensity on trailing window
    "attack_growth": 1.0,     # >=100% growth recent-2y avg vs prior-2y avg
    "attack_total": 200,      # and >=200 total works in window
}

# Ticker -> SEC CIK for node tickers we actually poll. Missing tickers are
# NOT guessed — they go to the unknowns ledger (see ensure_cik_coverage).
CIK_MAP = {
    "MU": "1430265",
    "NVDA": "1045810",
    "INTC": "50863",
    "AMD": "2488",
    "IONQ": "1527467",
    "RGTI": "1524447",
    "FORM": "103939",
    "KEYS": "1601046",
    "GFS": "1709048",
    "COHR": "820479",
    "LITE": "1301239",
    "AVGO": "1730168",
    "GOOGL": "1652044",
    "META": "1326801",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Nodes whose graph labels are not literature vocabulary get an explicit,
# auditable query override (label kept as-is; only the search string changes).
QUERY_OVERRIDES = {
    "quantum_ip": "quantum computing patents",
}


def short_query(label: str) -> str:
    """Searchable query: strip parentheticals/lists, keep the head clause."""
    head = (label or "").split("(")[0].split(":")[0]
    head = head.split(",")[0] if len(head.split(",")[0].split()) >= 2 else head
    return " ".join(head.split()).strip() or (label or "")


# Polymarket query overrides: node labels return loose earnings-call
# markets, so map to topical liquid queries (probed 2026-09-10; Gamma has
# no full-text search, matching is keyword-side). Re-probe periodically.
PM_QUERY_OVERRIDES = {
    "accelerators": "artificial intelligence",
    "trap_ion_qc": "quantum computer",
    "quantum_ip": "quantum computer",
    "power": "nuclear power",
    "memory_hbm": "semiconductor",
    "memory_dram": "semiconductor",
    "packaging": "semiconductor",
    "storage": "data center",
    "optical_io": "data center",
    "motors": "robot",
    "reducers": "robot",
    "encoders": "robot",
    "bearings": "robot",
    "torque_sensing": "robot",
}


def node_queries(node: dict) -> dict:
    """Live-query strings derived from the node (no hand lists to rot)."""
    nid = node.get("id", "")
    oa = QUERY_OVERRIDES.get(nid,
                             short_query(node.get("label", nid)))
    pm = PM_QUERY_OVERRIDES.get(nid, short_query(node.get("label", nid)))
    return {"openalex": oa, "polymarket": pm}


def ensure_cik_coverage(nodes: list[dict]) -> list[str]:
    """Tickers on graph nodes with no CIK entry -> unknowns ledger + return.
    Idempotent: skips subjects already open."""
    known = {u.get("subject", "") for u in E.read_unknowns(open_only=False)}
    open_subjects = {u.get("subject", "") for u in E.read_unknowns()}
    missing: list[str] = []
    for n in nodes:
        for t in n.get("tickers", []):
            if t and t not in CIK_MAP and t not in missing:
                missing.append(t)
    for t in missing:
        if f"SEC CIK for {t}" not in known:
            E.add_unknown(subject=f"SEC CIK for {t}",
                          sought="10-digit CIK for submissions JSON polling",
                          searched="bneck2/killfeed.py CIK_MAP",
                          would_close_it=f"Form 4 / 8-K burst coverage for {t}")
    return missing


def attack_intensity(velocity: dict) -> dict:
    """AttackIntensity numbers from one OpenAlex velocity page.

    growth = recent-2y mean / prior-2y mean - 1 over per_year counts.
    tier HIGH needs both growth and mass (no hype without a literature).

    Peer-review P1 fix: the current calendar year is EXCLUDED (partial-year
    counts systematically depress growth). Needs >=4 complete years.
    """
    per_year = velocity.get("per_year", {}) or {}
    current = datetime.now(timezone.utc).year
    years = sorted(int(y) for y in per_year
                   if str(y).isdigit() and int(y) < current)
    counts = [int(per_year.get(y, per_year.get(str(y), 0))) for y in years]
    growth = 0.0
    if len(counts) >= 4:
        recent = sum(counts[-2:]) / 2.0
        prior = sum(counts[-4:-2]) / 2.0
        growth = (recent / prior - 1.0) if prior > 0 else 0.0
    total = int(velocity.get("total_works", 0))
    tier = ("HIGH" if growth >= THRESHOLDS["attack_growth"]
            and total >= THRESHOLDS["attack_total"] else "normal")
    return {"growth": round(growth, 3), "total": total, "tier": tier,
            "years_seen": len(years), "excluded_year": current}


def _attack_rows(nid: str, ts: str, velocity: dict) -> list[dict]:
    a = attack_intensity(velocity)
    return [{"ts": ts, "node_id": nid,
             "signal": "openalex-attack(growth>=%.1f,total>=%d)"
             % (THRESHOLDS["attack_growth"], THRESHOLDS["attack_total"]),
             "measured": f"growth={a['growth']} total={a['total']}",
             "threshold": "HIGH needs growth AND mass",
             "verdict": "TRIGGERED" if a["tier"] == "HIGH" else "NOT TRIGGERED",
             "source": "openalex"}]


def sec_burst(all_filings: list[dict], baseline: dict | None = None) -> dict:
    """Burst counts across one node's ticker filings (one poll window).

    Verdict stays absolute (gates depend on it). When a baseline
    {med_form4, med_deal} is supplied, measured carries vs_base ratios so
    routine-cadence names (NVDA files constantly) read differently from
    genuine inflections. Calibration note, not verdict."""
    forms = [f.get("form", "") for f in all_filings]
    n4 = sum(1 for x in forms if x == "4")
    deal = sum(1 for x in forms if x in ("8-K", "13D", "13G"))
    out: dict = {"form4": n4, "deal": deal, "n": len(forms),
                 "form4_burst": n4 >= THRESHOLDS["sec_form4_burst"],
                 "deal_burst": deal >= THRESHOLDS["sec_deal_burst"]}
    if baseline:
        mf = max(float(baseline.get("med_form4", 0)), 0.5)
        md = max(float(baseline.get("med_deal", 0)), 0.5)
        out["vs_base"] = f"{n4 / mf:.1f}x/{deal / md:.1f}x"
    return out


def load_baselines(path: Path = BASELINES_PATH) -> dict:
    try:
        import json as _j
        return _j.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def record_baselines(counts: dict[str, dict], ts: str,
                     path: Path = BASELINES_PATH) -> dict:
    """counts: ticker -> {form4, deal}. Appends, caps history. Returns medians."""
    import json as _j
    try:
        doc = _j.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    for t, c in counts.items():
        hist = doc.setdefault(t, [])
        hist.append({"ts": ts, "form4": c["form4"], "deal": c["deal"]})
        del hist[:-BASELINE_KEEP]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_j.dumps(doc, indent=1), encoding="utf-8")
    return baseline_medians(doc)


def baseline_medians(doc: dict) -> dict[str, dict]:
    med: dict[str, dict] = {}
    for t, hist in doc.items():
        if not hist:
            continue
        f4 = sorted(h["form4"] for h in hist)
        dl = sorted(h["deal"] for h in hist)
        med[t] = {"med_form4": float(f4[len(f4) // 2]),
                  "med_deal": float(dl[len(dl) // 2]), "n": len(hist)}
    return med


def load_seen(path: Path = SEEN_PATH) -> dict:
    try:
        import json as _j
        doc = _j.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def split_unseen(cik: str, filings: list[dict],
                 seen: dict | None = None) -> tuple[list[dict], dict]:
    """Partition filings into (new, updated-seen-store). Pure function:
    unit of evidence is the accession number (peer-review P0 fix)."""
    seen = dict(seen) if seen else {}
    have = set(seen.get(cik, []))
    new = [f for f in filings if f.get("accession") and f["accession"] not in have]
    seen[cik] = sorted(have | {f["accession"] for f in new})
    return new, seen


def save_seen(seen: dict, path: Path = SEEN_PATH) -> None:
    import json as _j
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_j.dumps(seen, indent=1), encoding="utf-8")


PM_LINKS_PATH = ROOT / "data" / "pm_links.json"


def _pm_links(path: Path = PM_LINKS_PATH) -> list[dict]:
    try:
        import json as _j
        doc = _j.loads(path.read_text(encoding="utf-8"))
        return doc.get("links", []) if isinstance(doc, dict) else []
    except (OSError, ValueError):
        return []


def link_market(question: str, links: list[dict] | None) -> dict | None:
    """Typed causal edge market -> node, or None (= discovery-grade).
    Links are passed in by the caller (run loads them once); evaluation
    never touches disk itself."""
    q = (question or "").lower()
    for link in links or []:
        if str(link.get("match", "")).lower() in q:
            return link
    return None


def pm_reading(snapshots: list[dict],
               links: list[dict] | None = None) -> dict | None:
    """Best-book read over MarketSnapshots. PURE: no imports, no sockets,
    no files. Snapshot enrichment (Gamma details + CLOB depth) happens in
    collectors/snapshots.py before this is ever called.

    Peer-review P1 fix: a probability is NOT directional evidence. The
    reading carries an evidence grade — "linked" only when the caller
    supplies a typed link (node + polarity) for the question; otherwise
    "discovery" (logged, never fused into belief updates)."""
    if not snapshots:
        return None
    best = max(snapshots, key=lambda m: (float(m.get("liquidity", 0)),
                                         float(m.get("volume", 0))))
    tier = best.get("tier") or "low-liquidity"
    rel = CAL.pm_reliability(best.get("venue", ""), tier)
    depth = float(best.get("depth_top5", 0) or 0)
    spread = best.get("spread")
    depth_note = ""
    if depth or spread is not None:
        depth_note = f" depth=${depth:,.0f} spread={spread}"
        if depth >= 1_000_000:
            rel = min(rel + 0.1, 0.95)
        if (spread or 0) > 0.2:
            rel = max(rel - 0.1, 0.3)
    link = link_market(best.get("question", ""), links)
    grade = "linked" if link else "discovery"
    return {"question": (best.get("question") or "")[:160],
            "p": float(best.get("p", 0.0)), "tier": tier,
            "venue": str(best.get("venue", "?")) + depth_note,
            "reliability": round(rel, 3),
            "conditionId": best.get("conditionId") or "",
            "source_hash": best.get("source_hash", ""),
            "evidence_grade": grade,
            "link": {"node": link.get("node"), "polarity": link.get("polarity"),
                     "relevance": link.get("relevance")} if link else None}


def evaluate(node: dict, sec: list[dict] | None = None,
             velocity: dict | None = None,
             markets: list[dict] | None = None,
             ts: str = "", sec_baseline: dict | None = None,
             whales: list[dict] | None = None,
             pm_links: list[dict] | None = None) -> list[dict]:
    """Pure evaluation -> verdict rows (NOT yet written). `markets` must be
    MarketSnapshots (collectors/snapshots.py); `whales` pre-fetched
    consensus rows. No I/O here — enforced by tests/test_purity.py."""
    nid = node.get("id", "?")
    ts = ts or utcnow()
    rows: list[dict] = []
    if sec is not None:
        b = sec_burst(sec, sec_baseline)
        fired = b["form4_burst"] or b["deal_burst"]
        measured = f"form4={b['form4']} deal={b['deal']} n={b['n']} (new accessions)"
        if "vs_base" in b:
            measured += f" vs_base={b['vs_base']}"
        rows.append({"ts": ts, "node_id": nid,
                     "signal": "sec-burst(Form4>=%d,deal>=%d)"
                     % (THRESHOLDS["sec_form4_burst"],
                        THRESHOLDS["sec_deal_burst"]),
                     "measured": measured,
                     "threshold": "NEW filings since last poll (accession-deduped)",
                     "verdict": "TRIGGERED" if fired else "NOT TRIGGERED",
                     "source": "sec-edgar"})
    if velocity is not None:
        if not velocity.get("ok", True):
            rows.append({"ts": ts, "node_id": nid,
                         "signal": "openalex-attack(growth>=%.1f,total>=%d)"
                         % (THRESHOLDS["attack_growth"],
                            THRESHOLDS["attack_total"]),
                         "measured": "fetch failed",
                         "threshold": "HIGH needs growth AND mass",
                         "verdict": "INCONCLUSIVE",
                         "source": "openalex"})
        else:
            rows.extend(_attack_rows(nid, ts, velocity))
    if markets is not None:
        r = pm_reading(markets, pm_links)
        if r is None:
            rows.append({"ts": ts, "node_id": nid, "signal": "pm-clock",
                         "measured": "no markets returned",
                         "threshold": "any book", "verdict": "INCONCLUSIVE",
                         "source": "polymarket"})
        else:
            rows.append({"ts": ts, "node_id": nid, "signal": "pm-clock",
                         "measured": f"p={r['p']} {r['tier']} "
                         f"{r.get('venue', '?')} rel={r['reliability']} "
                         f"grade={r.get('evidence_grade', 'discovery')}: "
                         f"{r['question']}",
                         "threshold": "best-book read, never p alone",
                         "verdict": "NOT TRIGGERED",
                         "source": "polymarket",
                         "_emit_signal": {"type": "PM_CLOCK", "direction": 0,
                                          "strength": r["p"],
                                          "confidence": r["reliability"]}})
            # Whale consensus on the best-book market (pre-fetched by run()).
            for c in (whales or [])[:1]:
                rows[-1].setdefault("_extra_signals", []).append(
                    {"type": "WHALE_CONSENSUS", "direction": 0,
                     "strength": min(1.0, float(c.get("total_usd", 0)) / 50000.0),
                     "confidence": round(0.55 + 0.05 * min(int(c.get("n_wallets", 0)), 5), 2),
                     "note": f"{c.get('n_wallets')} whales ${float(c.get('total_usd', 0)):,.0f} "
                     f"outcome={c.get('outcome')}: {c.get('question', '')}"})
    return rows


def write_rows(rows: list[dict]) -> int:
    n = 0
    for r in rows:
        E.log_kill_observation(r["node_id"], r["signal"], r["measured"],
                               r["threshold"], r["verdict"],
                               source=r.get("source", ""), ts=r.get("ts", ""))
        n += 1
        sig = r.pop("_emit_signal", None)
        if sig:
            E.log_signal(r["node_id"], sig["type"], sig["direction"],
                         sig["strength"], sig["confidence"],
                         source=r.get("source", ""), ts=r.get("ts", ""))
        for extra in r.pop("_extra_signals", []) or []:
            E.log_signal(r["node_id"], extra["type"], extra["direction"],
                         extra["strength"], extra["confidence"],
                         source=r.get("source", "")
                         + ("|" + extra["note"] if extra.get("note") else ""),
                         ts=r.get("ts", ""))
    return n


def run(live: bool = False, write: bool = True,
        max_nodes: int = 0, sleep_s: float = 1.0) -> dict:
    """The loop. live=False evaluates nothing (no caches yet) but still
    ensures CIK coverage unknowns. live=True collects per node, best-effort,
    then evaluates + writes verdicts. Returns a summary dict."""
    g = G.load_graph()
    nodes = g.get("nodes", [])
    if max_nodes:
        nodes = nodes[:max_nodes]
    missing_ciks = ensure_cik_coverage(g.get("nodes", []))
    summary = {"nodes": len(nodes), "missing_ciks": missing_ciks,
               "verdicts": 0, "triggered": [], "live": live}
    if not live:
        return summary
    from collectors import sec as SEC
    from collectors import openalex as OA
    from collectors import polymarket as PM
    from collectors import kalshi as KL
    from collectors import polywhale as PW
    from collectors import snapshots as SNAP
    from bneck2 import migration as MIG
    from bneck2 import quant as Q
    run_ts = utcnow()
    readings = Q.load_readings()
    links = _pm_links()
    medians = baseline_medians(load_baselines())
    seen = load_seen()
    ticker_counts: dict[str, dict] = {}
    for n in nodes:
        filings: list[dict] = []
        for t in n.get("tickers", []):
            cik = CIK_MAP.get(t)
            if cik:
                got = SEC.fetch_recent_filings(cik)
                new_got, seen = split_unseen(cik, got, seen)
                f4 = sum(1 for f in new_got if f.get("form") == "4")
                dl = sum(1 for f in new_got if f.get("form") in ("8-K", "13D", "13G"))
                ticker_counts[t] = {"form4": f4, "deal": dl}
                filings.extend(new_got)
                time.sleep(0.2)
        node_base = None
        tick_meds = [medians[t] for t in n.get("tickers", []) if t in medians]
        if tick_meds:
            node_base = {
                "med_form4": sum(m["med_form4"] for m in tick_meds) / len(tick_meds),
                "med_deal": sum(m["med_deal"] for m in tick_meds) / len(tick_meds)}
        q = node_queries(n)
        vel = OA.fetch_yearly(q["openalex"])
        time.sleep(sleep_s)
        mkts = PM.fetch_markets(q["polymarket"])
        for m in mkts:
            m.setdefault("venue", "polymarket")
        time.sleep(sleep_s)
        try:
            mkts = mkts + KL.fetch_markets(q["polymarket"])
        except Exception:
            pass
        time.sleep(sleep_s)
        snaps = SNAP.snapshot_all(mkts, limit=3, sleep_s=0.5)
        best = pm_reading(snaps)
        whales: list[dict] = []
        if best and best.get("conditionId"):
            try:
                whales = PW.consensus(
                    [{"question": best["question"],
                      "conditionId": best["conditionId"], "p": best["p"]}])[:1]
            except Exception:
                whales = []
        rows = evaluate(n, sec=filings, velocity=vel, markets=snaps,
                        sec_baseline=node_base, whales=whales,
                        pm_links=links)
        if write:
            summary["verdicts"] += write_rows(rows)
            sev = MIG.severity(n, readings.get(n.get("id", "")))
            MIG.record_severity(n.get("id", "?"), sev["B"], run_ts)
        summary["triggered"].extend(
            f"{n.get('id')}:{r['signal']}" for r in rows
            if r["verdict"] == "TRIGGERED")
    if live and write and ticker_counts:
        summary["baselines"] = record_baselines(ticker_counts, run_ts)
    if live and write:
        save_seen(seen)
    return summary


def render_summary(summary: dict) -> str:
    lines = [f"# killfeed loop — live={summary['live']} "
             f"nodes={summary['nodes']} verdicts={summary['verdicts']}"]
    if summary["missing_ciks"]:
        lines.append("CIKs missing (unknowns ledger): "
                     + ", ".join(summary["missing_ciks"]))
    if summary["triggered"]:
        lines.append("TRIGGERED:")
        lines.extend(f"  !! {t}" for t in summary["triggered"])
    else:
        lines.append("no TRIGGERED verdicts this pass.")
    return "\n".join(lines)
