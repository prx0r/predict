"""HF Stocks-Daily-Price panel fetcher (stdlib only).

Table is sorted by (symbol, date); binary-search each symbol's block via
/rowsoft datasets-server, page length=100, keep date>=START. Cache JSONL:
data/hf_panel/daily.jsonl (one row per symbol-date). Resume-safe: skips
symbols already fully cached (marker file per symbol).
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import urllib.error
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "hf_panel"
DS = "paperswithbacktest/Stocks-Daily-Price"
API = "https://datasets-server.huggingface.co/rows"
TOTAL = 25986919
START = "2016-01-01"

UNIVERSE = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA",
            "AVGO", "AMD", "NFLX", "CRM", "ORCL", "PLTR", "COIN",
            "INTC", "IBM", "JPM", "V", "MA", "XOM", "JNJ", "WMT",
            "PG", "UNH", "HD", "BAC", "DIS", "ADBE", "ABT", "KO",
            "LLY", "MRK", "PEP", "COST", "TMO", "CSCO", "ACN",
            "2360.TW", "FORM", "KEYS", "KLAC", "NVMI", "CAMT",
            "BRKR", "AEHR", "ONTO", "AMAT", "LRCX", "MU", "QCOM",
            "TXN", "ADI", "MRVL", "ARM", "SMCI", "DELL", "HPE",
            "NBIS", "COHR", "IAG", "MPAL", "ACCO", "TSCO"]


import time as _time

LAST_CALL = [0.0]


def _get(params: dict, tries: int = 8) -> dict:
    q = urllib.parse.urlencode(params)
    for k in range(tries):
        dt = _time.time() - LAST_CALL[0]
        if dt < 1.0:
            _time.sleep(1.0 - dt)
        req = urllib.request.Request(API + "?" + q,
                                     headers={"User-Agent": "bneck"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                LAST_CALL[0] = _time.time()
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            wait = 2 ** k * 5
            try:
                ra = e.headers.get("Retry-After")
                if ra:
                    wait = max(wait, int(ra))
            except Exception:
                pass
            _time.sleep(wait)
    raise RuntimeError("datasets-server rate limit persists")


def _sym_at(idx: int) -> tuple[str, str]:
    r = _get({"dataset": DS, "config": "default", "split": "train",
              "offset": str(max(idx, 0)), "length": "1"})
    row = r["rows"][0]["row"]
    return row["symbol"], row["date"]


def find_block(sym: str, hint: int = 0) -> tuple[int, int] | None:
    lo, hi = max(hint, 0), TOTAL - 1
    first = TOTAL
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            s, _ = _sym_at(mid)
        except Exception:
            return None
        if s < sym:
            lo = mid + 1
        elif s > sym:
            hi = mid - 1
        else:
            first = mid
            hi = mid - 1
    if first == TOTAL:
        return None
    lo, hi = first, TOTAL - 1
    last = first
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            s, _ = _sym_at(mid)
        except Exception:
            hi = mid - 1
            continue
        if s == sym:
            last = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return first, last


def fetch_symbol(sym: str) -> dict:
    done = OUT / f".done_{sym.replace('/', '_')}"
    if done.exists():
        return {"symbol": sym, "cached": True}
    blk = find_block(sym)
    if not blk:
        return {"symbol": sym, "rows": 0, "missing": True}
    first, last = blk
    kept = []
    off = first
    while off <= last:
        try:
            r = _get({"dataset": DS, "config": "default",
                      "split": "train", "offset": str(off),
                      "length": "100"})
        except Exception:
            break
        for x in r.get("rows", []):
            row = x["row"]
            if row["symbol"] != sym:
                break
            if row["date"] >= START and row.get("adj_close"):
                kept.append({"s": sym, "d": row["date"],
                             "c": round(row["adj_close"], 4),
                             "v": row.get("volume") or 0})
        else:
            off += 100
            continue
        break
    with (OUT / "daily.jsonl").open("a") as f:
        for k in kept:
            f.write(json.dumps(k) + "\n")
    done.touch()
    return {"symbol": sym, "rows": len(kept)}


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    uni = sys.argv[1:] or UNIVERSE
    out, hint = [], 0
    for sym in sorted(uni):
        try:
            blk = find_block(sym, hint)
        except RuntimeError:
            out.append({"symbol": sym, "rows": 0, "error": True})
            continue
        if blk:
            hint = blk[1]
        # fetch via direct block walk (no re-search inside)
        import os as _os
        done = OUT / f".done_{sym.replace('/', '_')}"
        if done.exists():
            out.append({"symbol": sym, "cached": True})
            continue
        if not blk:
            out.append({"symbol": sym, "rows": 0, "missing": True})
            continue
        first, last = blk
        kept, off = [], first
        ok = True
        while off <= last:
            try:
                r = _get({"dataset": DS, "config": "default",
                          "split": "train", "offset": str(off),
                          "length": "100"})
            except RuntimeError:
                ok = False
                break
            for x in r.get("rows", []):
                row = x["row"]
                if row["symbol"] != sym:
                    break
                if row["date"] >= START and row.get("adj_close"):
                    kept.append({"s": sym, "d": row["date"],
                                 "c": round(row["adj_close"], 4),
                                 "v": row.get("volume") or 0})
            else:
                off += 100
                continue
            break
        if ok:
            with (OUT / "daily.jsonl").open("a") as f:
                for k in kept:
                    f.write(json.dumps(k) + "\n")
            done.touch()
            out.append({"symbol": sym, "rows": len(kept)})
        else:
            out.append({"symbol": sym, "rows": 0, "error": True})
    return {"symbols": len(out),
            "rows": sum(x.get("rows", 0) for x in out),
            "missing": [x["symbol"] for x in out if x.get("missing")]}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
