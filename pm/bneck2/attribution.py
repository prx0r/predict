"""Price attribution on the dependency chain (stdlib only).

Why is it going up? Decompose a ticker's window return into market part
(beta x SPY), layer part (layer-mates mean excess), and idiosyncratic rest;
then read demand state (ProphetMap pricingScore drift, PEG band, funnel)
over the same window. Same chain models the break: flags fire when price
and demand-state diverge. Panel: 94 daily ProphetMap score snapshots.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORES = ROOT / "third_party" / "prophetmap" / "data" / "scores"


def load_panel() -> dict:
    """{symbol: {dates, price, score, peg, funnel, layer}} from snapshots."""
    panel: dict[str, dict[str, list]] = {}
    for f in sorted(glob.glob(str(SCORES / "*.json"))):
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            continue
        date = d.get("date", Path(f).stem)
        for r in d.get("results", []):
            s = r.get("symbol")
            if not s:
                continue
            p = panel.setdefault(s, {"dates": [], "price": [], "score": [],
                                     "peg": [], "funnel": [], "layer": ""})
            p["dates"].append(date)
            p["price"].append(r.get("price"))
            p["score"].append(r.get("pricingScore"))
            p["peg"].append(r.get("pegBand"))
            p["funnel"].append(r.get("funnelPass"))
            p["layer"] = r.get("layer", "")
    return panel


def _r2(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 10:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    if vx <= 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vy = sum((y - my) ** 2 for y in ys)
    return round((cov * cov) / (vx * vy) if vy > 0 else 0.0, 3)


def _rets(px: list) -> list[float]:
    out = []
    for a, b in zip(px[:-1], px[1:]):
        if a and b:
            out.append(b / a - 1)
    return out


def attribute(symbol: str, panel: dict | None = None) -> dict:
    import sys
    sys.path.insert(0, str(ROOT))
    from bneck2 import prices as P
    panel = panel if panel is not None else load_panel()
    if symbol not in panel or len(panel[symbol]["dates"]) < 30:
        return {"ticker": symbol, "error": "no panel (need 30+ snapshots)"}
    me = panel[symbol]
    layer = me["layer"]
    mates = [s for s, v in panel.items()
             if v["layer"] == layer and s != symbol and len(v["dates"]) >= 30]
    # layer-mate mean price path (aligned by date)
    by_date: dict[str, list] = {}
    for m in mates:
        for d, p in zip(panel[m]["dates"], panel[m]["price"]):
            if p:
                by_date.setdefault(d, []).append(p)
    my_dates = sorted(set(me["dates"]) & set(by_date))
    lay_ret = []
    for a, b in zip(my_dates[:-1], my_dates[1:]):
        pa = sum(by_date[a]) / len(by_date[a])
        pb = sum(by_date[b]) / len(by_date[b])
        lay_ret.append(pb / pa - 1)
    own = [p for d, p in zip(me["dates"], me["price"]) if d in set(my_dates)]
    own_ret = _rets(own)
    try:
        spy = {c["date"]: c["close"]
               for c in P.history("SPY", "6mo").get("closes", [])}
        spy_ret = []
        for a, b in zip(my_dates[:-1], my_dates[1:]):
            if a in spy and b in spy and spy[a]:
                spy_ret.append(spy[b] / spy[a] - 1)
    except Exception:
        spy_ret = []
    n = min(len(own_ret), len(lay_ret), len(spy_ret))
    r2_mkt = _r2(spy_ret[-n:], own_ret[-n:]) if n >= 10 else 0.0
    r2_lay = _r2(lay_ret[-n:], own_ret[-n:]) if n >= 10 else 0.0
    total = (own[-1] / own[0] - 1) if own[0] else 0.0
    scores = [s for s in me["score"] if s is not None]
    drift = (scores[-1] - scores[0]) if len(scores) >= 2 else None
    flags = []
    if total > 0.15 and (drift or 0) < -0.3:
        flags.append("PRICE-UP-SCORE-DOWN: rising on weakening demand read")
    if (me["peg"] or [None])[-1] == "rich" and total > 0.3:
        flags.append("RICH-MULTIPLE: extended on rich PEG band")
    if (me["funnel"] or [None])[-1] is False:
        flags.append("FUNNEL-FAIL: fails ProphetMap funnel now")
    if total < -0.2 and (drift or 0) > 0.3:
        flags.append("PRICE-DOWN-SCORE-UP: washed out while demand read improves")
    return {"ticker": symbol, "window_days": len(my_dates),
            "total": round(total, 4), "r2_market": r2_mkt,
            "r2_layer": r2_lay,
            "idio_share": round(max(1 - r2_mkt - r2_lay, 0.0), 3),
            "score_drift": round(drift, 3) if drift is not None else None,
            "peg": (me["peg"] or [None])[-1],
            "funnel": (me["funnel"] or [None])[-1],
            "mates": len(mates), "flags": flags}


def monitor(tickers: list[str]) -> dict:
    panel = load_panel()
    out = {}
    for t in tickers:
        try:
            out[t] = attribute(t, panel)
        except Exception as e:
            out[t] = {"ticker": t, "error": str(e)[:100]}
    return {"asof": panel.get(tickers[0], {}).get("dates", ["?"])[-1]
            if tickers else "?", "attribution": out}
