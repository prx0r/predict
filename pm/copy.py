"""Copy engine — Jev decides what to mirror, paper only.

Per candidate copy event (tracked wallet traded):
  state    = wallet stats + market divergence + book + edge estimate
  questions= action {copy, watch, skip} + size {none, small, standard}
Jev returns typed answers; code logs the decision. No execution path
exists in this file — paper log only, human reads before anything real.

Usage:
    OPENROUTER_API_KEY=... python3 pm/copy.py --wallets 0xabc.. --limit 5
    Wallets as 0x addresses (see PEOPLE.md / trader pages).
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pm"))

from judge import jev_decide  # noqa: E402

DATA_API = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
JEV_MODEL = "typesafe/jev-1.13"

COPY_QUESTIONS = {
    "action": {
        "type": "choice",
        "instructions": "What should the paper desk do about this wallet trade?",
        "criteria": {
            "copy": "follow the trade: proven wallet, clean conditions, payable spread",
            "watch": "interesting but missing something (thin book, vague text, small edge)",
            "skip": "do not follow: bad conditions, bad price, or unresolvable ambiguity",
        },
    },
    "size": {
        "type": "choice",
        "instructions": "If copying, what paper size?",
        "criteria": {
            "none": "no position",
            "small": "half unit: edge thin or confidence moderate",
            "standard": "full paper unit: clear edge, clean text, good book",
        },
    },
}

# politics-board specialists (name -> 0x), scraped 2026-09-23.
WALLETS = {
    "e46m3": "0x4f1d5ae26fc31472966e951af3183308736d8de2",
    "RN1": "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",
    "balthazar": "0x5a218c7ad04135830a45c41aaed7294df7809318",
    "ndb1": "0xfea31bc088000ff909be1dfd8d0e3f2c7ef2d227",
}


def get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": "predict-copy"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def recent_trades(addr: str, limit: int = 5):
    try:
        d = get(f"{DATA_API}/trades?user={addr}&limit={limit}")
        return d if isinstance(d, list) else []
    except Exception:
        return []


def divergence_for(condition_id: str):
    for fp in glob.glob(str(ROOT / "data" / "resolutions" / "*.json")):
        if fp.endswith("_sweep_stats.json"):
            continue
        try:
            r = json.load(open(fp))
        except ValueError:
            continue
        if (r.get("conditionId") or "").lower() == condition_id.lower():
            return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallets", default="e46m3,RN1")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    outdir = ROOT / "data" / "paper"
    outdir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    with open(outdir / f"copy-decisions-{day}.jsonl", "a") as fh:
        for name in [w.strip() for w in args.wallets.split(",") if w.strip()]:
            addr = WALLETS.get(name, name)
            trades = recent_trades(addr, args.limit)
            print(f"  [{name}] {len(trades)} recent trades")
            for t in trades:
                cid = t.get("conditionId", "")
                rec = divergence_for(cid)
                div = rec.get("divergence") if rec else None
                state = (
                    f"WALLET: {name} (tracked specialist)\n"
                    f"TRADE: {t.get('side')} {(t.get('title') or '')[:90]} "
                    f"@ {t.get('price')} size {t.get('size')}\n"
                    f"RESOLUTION DIVERGENCE: {div if div is not None else 'unscored'}"
                    f"{' — ' + (rec.get('question') or '')[:60] if rec else ''}\n"
                    f"EXCLUSIONS: {len((rec or {}).get('exclusions', []))} carve-outs; "
                    f"SOURCE: {(rec or {}).get('resolution_source') or 'unstated'}"
                )
                try:
                    ans = jev_decide(state, COPY_QUESTIONS, model=JEV_MODEL)
                except Exception as e:
                    print(f"    JUDGE ERR {str(e)[:80]}")
                    continue
                act = (ans.get("action") or {}).get("choice")
                size = (ans.get("size") or {}).get("choice")
                if act != "copy":
                    size = "none"  # judges answer independently; code enforces consistency
                row = {"at": datetime.now(timezone.utc).isoformat(),
                       "wallet": name, "title": (t.get("title") or "")[:80],
                       "side": t.get("side"), "price": t.get("price"),
                       "divergence": div,
                       "action": act,
                       "size": size,
                       "judge": JEV_MODEL}
                fh.write(json.dumps(row) + "\n")
                print(f"    {row['action']}/{row['size']} :: {row['title'][:55]}")
                n += 1
                time.sleep(2)
    print(f"[COPY] {n} decisions logged (key never stored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
