"""Selective book pulls — trentmkelly depth, filtered to tracked tokens.

Never mirrors. Resolves our conditionIds -> clobTokenIds via Gamma,
lists recent depth runs via HF API, downloads, keeps only rows for
our tokens, stores Parquet under data/books/date=YYYY-MM-DD/.

Disk guardrail: ~90KB/run raw, filtered output far smaller.

Usage:
    python3 pm/pull_books.py --conditions 0xabc... 0xdef... [--runs 12]
    python3 pm/pull_books.py --from-records data/resolutions
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"
HF_API = "https://huggingface.co/api/datasets/trentmkelly/polymarket_historical_data"
HF_FILE = ("https://huggingface.co/datasets/trentmkelly/"
           "polymarket_historical_data/resolve/main/{path}")


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "predict-pull"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def tokens_for_slug(slug: str) -> list:
    """Event slug -> clobTokenIds. NOTE: /markets?condition_id= IGNORES
    its filter (verified: returned an unrelated market) — never use it."""
    try:
        doc = json.loads(get(f"{GAMMA}/events/slug/{slug}"))
    except Exception:
        return []
    out = []
    for m in doc.get("markets", [doc] if isinstance(doc, dict) else []):
        try:
            out.extend(json.loads(m.get("clobTokenIds") or "[]"))
        except (ValueError, TypeError):
            continue
    return out


def recent_runs(n: int = 12) -> list:
    doc = json.loads(get(HF_API, timeout=30).decode())
    files = sorted(s["rfilename"] for s in doc.get("siblings", [])
                   if "/order_book_depth/" in s["rfilename"])
    return files[-n:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", nargs="*", default=[])
    ap.add_argument("--from-records", default=None)
    ap.add_argument("--runs", type=int, default=12)
    args = ap.parse_args()

    cids = list(args.conditions)
    slugs = []
    if args.from_records:
        for fp in glob.glob(f"{args.from_records}/*.json"):
            if fp.endswith("_sweep_stats.json"):
                continue
            try:
                r = json.load(open(fp))
            except ValueError:
                continue
            slugs.append(r.get("slug"))
            cids.extend(r.get("clobTokenIds") or [])
    cids = list(dict.fromkeys(cids))
    print(f"[PULL] {len(cids)} condition/token ids")
    slugs = [s for s in dict.fromkeys(slugs) if s]

    tokens: set = set()
    for cid in cids:
        if len(cid) > 20 and cid.isdigit():
            tokens.add(cid)  # already a token id
            continue
    for s in slugs:
        for t in tokens_for_slug(s):
            tokens.add(str(t))
    print(f"[PULL] {len(tokens)} clob tokens")

    import subprocess
    tmp = ROOT / "data" / "_tmp_books"
    tmp.mkdir(parents=True, exist_ok=True)
    runs = recent_runs(args.runs)
    print(f"[PULL] {len(runs)} depth runs")
    kept = 0
    try:
        import pyarrow.parquet as pq
        import pyarrow as pa
    except ImportError:
        print("[PULL] need pyarrow (`pip install pyarrow`)")
        return 1
    for rel in runs:
        lp = tmp / Path(rel).name
        try:
            raw = get(HF_FILE.format(path=rel), timeout=120)
            lp.write_bytes(raw)
            t = pq.read_table(str(lp))
            import pyarrow.compute as pc
            t = t.filter(pc.is_valid(t.column("asset_id")))
            keep = t.filter(pc.is_in(t.column("asset_id").cast(pa.string()),
                                     pa.array(sorted(tokens))))
            if keep.num_rows:
                day = rel.split("date=")[1].split("/")[0]
                outdir = ROOT / "data" / "books" / f"date={day}"
                outdir.mkdir(parents=True, exist_ok=True)
                pq.write_table(keep, outdir / lp.name)
                kept += keep.num_rows
        except Exception as e:
            print(f"  [SKIP] {rel.split('/')[-1]}: {str(e)[:80]}")
        finally:
            lp.unlink(missing_ok=True)
    print(f"[PULL] kept {kept} rows for our tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
