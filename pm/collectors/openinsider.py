"""OpenInsider collector — insider screener reads, keyless ($0).

http://openinsider.com (plain HTTP; 443 refused from some nets).
Pages: /screener?s=TICKER, /latest-insider-trading,
/latest-cluster-buys, /latest-officer-purchases-25k.
Table.tinytable: header h3 row + <tr style> body rows (no </tbody>).
Recipes ex-third_party/openinsider-mcp (cheerio ported to stdlib regex).
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request

BASE = "http://openinsider.com"
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "Chrome/126.0 Safari/537.36")}


def _ticker(raw: str) -> str:
    m = re.search(r"<a[^>]*>([A-Z][A-Z0-9.\-]{0,7})</a>", raw or "")
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][A-Z0-9.\-]{0,7})\b",
                  re.sub(r"Tip\('.*?'\)", "", raw or ""))
    return m.group(1) if m else ""


def _clean(cell: str) -> str:
    cell = re.sub(r"""\son\w+="(?:[^"]|'[^']*')*" """, " ", cell)
    cell = re.sub(r"""\son\w+="(?:[^"]|'[^']*')*" """, " ", cell)
    return re.sub(r"<[^>]+>", "", cell).replace("&nbsp;", " ").strip()


def parse_table(html: str) -> list[dict]:
    i = html.find('class="tinytable"')
    if i < 0:
        return []
    seg = html[i:i + 200000]
    heads = [_clean(h).lower().replace(" ", "")
             for h in re.findall(r"<h3>(.*?)</h3>", seg)]
    out = []
    for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", seg, re.S):
        row = rm.group(1)
        if "<th" in row:
            continue
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 8:
            continue
        d = dict(zip(heads, cells))
        try:
            val = float((d.get("value", "0") or "0").replace("$", "").replace(",", "").replace("+", ""))
        except ValueError:
            val = 0.0
        out.append({"filing_date": d.get("filingdate", "")[:16],
                    "trade_date": d.get("tradedate", "")[:10],
                    "ticker": _ticker(d.get("ticker", "")),
                    "insider": d.get("insidername", "")[:60],
                    "title": d.get("title", "")[:40],
                    "trade_type": d.get("tradetype", ""),
                    "price": d.get("price", ""), "qty": d.get("qty", ""),
                    "value_usd": val,
                    "is_sale": "sale" in d.get("tradetype", "").lower(),
                    "is_buy": "purchase" in d.get("tradetype", "").lower()})
    return out


def fetch(path: str, timeout: int = 30) -> list[dict]:
    try:
        url = path if path.startswith("http") else BASE + path
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return parse_table(r.read().decode("utf-8", "replace"))
    except Exception:
        return []


def by_ticker(ticker: str) -> list[dict]:
    return fetch(f"/screener?s={urllib.parse.quote(ticker)}")


def latest(limit: int = 60) -> list[dict]:
    return fetch("/latest-insider-trading")[:limit]


def cluster_buys() -> list[dict]:
    return fetch("/latest-cluster-buys")


def officer_buys() -> list[dict]:
    return fetch("/latest-officer-purchases-25k")


def insider_summary(trades: list[dict]) -> dict:
    buys = [t for t in trades if t["is_buy"]]
    sells = [t for t in trades if t["is_sale"]]
    return {"n": len(trades),
            "buy_usd": round(sum(t["value_usd"] for t in buys), 2),
            "sell_usd": round(sum(t["value_usd"] for t in sells), 2),
            "names": sorted({t["insider"] for t in trades if t["insider"]})[:10]}
