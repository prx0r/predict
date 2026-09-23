#!/usr/bin/env python3
"""Company sweep — the entire chain for any ticker, one prompt.

Usage: /usr/bin/python3 scripts/sweep.py GOOGL
Runs: SEC burst + OpenInsider tape + Nasdaq holders/insiders + FINRA
short + PM/Kalshi/Manifold books + whale consensus + HN heat + EFTS
mentions + XBRL fundamentals + price snapshot. Writes verdict rows
(node_id=ticker, source=sweep) + docs/SWEEP-<T>-<date>.md + stdout.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CIKS = {"NVDA": "1045810", "AMD": "2488", "MU": "1430265", "INTC": "50863",
        "AVGO": "1730168", "GOOGL": "1652044", "META": "1326801",
        "AMZN": "1018724", "CSCO": "858877", "IONQ": "1527467",
        "RGTI": "1524447", "FORM": "103939", "KEYS": "1601046",
        "GFS": "1709048", "COHR": "820479", "LITE": "1301239"}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: sweep.py TICKER [company query words...]")
        return 1
    t = sys.argv[1].upper()
    q = " ".join(sys.argv[2:]) or t
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    from bneck2 import evidence as E
    from bneck2 import killfeed as K
    from bneck2 import prices as P
    from collectors import efts, finra, hn
    from collectors import kalshi as KL
    from collectors import manifold as MF
    from collectors import nasdaq as NQ
    from collectors import openinsider as OI
    from collectors import polymarket as PM
    from collectors import polywhale as PW
    from collectors import sec_facts as SF

    lines = [f"# Sweep {t} — {ts[:10]}", ""]
    verdicts = []

    def V(signal, measured, threshold, verdict, source):
        verdicts.append(E.log_kill_observation(
            t, signal, measured, threshold, verdict, source=source, ts=ts))

    # 1. SEC burst
    cik = CIKS.get(t)
    if cik:
        from collectors import sec as S
        fl = S.fetch_recent_filings(cik)
        b = K.sec_burst(fl)
        fired = b["form4_burst"] or b["deal_burst"]
        V("sec-burst", f"form4={b['form4']} deal={b['deal']} n={b['n']}",
          "Form4>=5 or deal>=2", "TRIGGERED" if fired else "NOT TRIGGERED",
          "sec-edgar")
        lines.append(f"- SEC: form4={b['form4']} deal={b['deal']}")
    else:
        lines.append(f"- SEC: no CIK mapped (unknowns ledger candidate)")

    # 2. Insider tape
    tape = OI.by_ticker(t)[:100]
    s = OI.insider_summary(tape)
    buys = [x for x in tape if x["is_buy"]]
    lines.append(f"- Insider: {s['n']} rows, buys ${s['buy_usd']:,.0f} / "
                 f"sells ${s['sell_usd']:,.0f}; names: {', '.join(s['names'][:5])}")
    V("insider-tape", f"buys=${s['buy_usd']:,.0f} sells=${s['sell_usd']:,.0f}",
      "reads direction", "NOT TRIGGERED", "openinsider")
    time.sleep(0.5)

    # 3. Nasdaq holders + insider counts
    h = NQ.holders(t, 10)
    acc = NQ.accumulators(h.get("holders", []))
    ic = NQ.insider_counts(t)
    lines.append(f"- Holders: {h.get('inst_pct')} inst, {h.get('total_records')} records; "
                 f"accumulators: {len(acc)}")
    lines.append(f"- Insider counts: {json.dumps(ic.get('counts', {}))[:160]}")
    if acc:
        top = acc[0]
        V("institutional-accumulation",
          f"{top['owner']} {top['change_pct']:+.1f}%",
          ">=+2% single holder", "TRIGGERED", "nasdaq")
    time.sleep(0.5)

    # 4. Short flow
    sh = finra.daily_short([t]).get(t.upper(), {})
    lines.append(f"- Short: ratio={sh.get('short_ratio')} vol={sh.get('short_vol')} "
                 f"({sh.get('date', '?')})")
    time.sleep(0.5)

    # 5. Prediction books (3 venues, best wins)
    mkts = PM.fetch_markets(q)
    for m in mkts:
        m.setdefault("venue", "polymarket")
    try:
        mkts += KL.fetch_markets(q)
    except Exception:
        pass
    try:
        mkts += MF.fetch_markets(q, 5)
    except Exception:
        pass
    r = K.pm_reading(mkts)
    if r:
        lines.append(f"- PM best: p={r['p']} {r['tier']} {r.get('venue')} rel={r['reliability']}: "
                     f"{(r['question'] or '')[:90]}")
        E.log_signal(t, "PM_CLOCK", 0, r["p"], r["reliability"],
                     source="sweep", ts=ts)
    else:
        lines.append("- PM: no books found")
    time.sleep(0.5)

    # 6. Whale consensus on best-book market
    cons = []
    if r:
        best = next((m for m in mkts
                     if (m.get("question") or "")[:160] == r["question"]
                     and m.get("conditionId")), None)
        if best:
            cons = PW.consensus([best])[:2]
    for c in cons:
        lines.append(f"- Whales: {c['n_wallets']} ${c['total_usd']:,.0f} "
                     f"outcome={c['outcome']}: {c['question'][:70]}")
        E.log_signal(t, "WHALE_CONSENSUS", 0,
                     min(1.0, c["total_usd"] / 50000.0), 0.6,
                     source="sweep", ts=ts)
    if not cons:
        lines.append("- Whales: no consensus ≥3")

    # 7. HN heat + EFTS mentions + fundamentals + price
    hits = hn.fetch_stories(q, 10)
    heat = hn.narrative_heat(hits)
    lines.append(f"- HN: {heat['heat']} ({heat['stories']} stories, {heat['points']}pts)")
    mentions = efts.search(f'"{t}"', limit=5)
    lines.append(f"- EFTS: {len(mentions)} recent filings mention {t}")
    if cik:
        f = SF.fundamentals(cik)
        lines.append(f"- Fundamentals: rev TTM ${f.get('revenue_ttm') or '?'} "
                     f"growth={f.get('revenue_growth_1y')} R&D={f.get('rd_intensity')}")
    px = P.history(t, "5d").get("closes", [])
    if len(px) >= 2:
        mom = (px[-1]["close"] - px[0]["close"]) / px[0]["close"]
        lines.append(f"- Price: {px[-1]['close']} ({mom:+.1%} 5d)")
    else:
        lines.append("- Price: unavailable")

    body = "\n".join(lines) + "\n"
    out = ROOT / "docs" / f"SWEEP-{t}-{ts[:10]}.md"
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"verdicts={len(verdicts)} report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
