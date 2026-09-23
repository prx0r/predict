"""X gateway — budget-enforced GetXAPI client, stdlib (BEAR pattern port).

Every call: budget check first, 2.1s rate limit, ledger append. Costs:
advanced_search/user_tweets $0.001/page, complete $0.003, detail $0.001,
thread $0.005, replies $0.001/page, user_info $0.001. Key NEVER logged.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = ROOT / "data" / "x" / "budget.json"
LEDGER = ROOT / "data" / "x" / "ledger.jsonl"
BASE = "https://api.getxapi.com"

COSTS = {
    "advanced_search": 0.001, "user_tweets": 0.001,
    "user_tweets_complete": 0.003, "tweet_detail": 0.001,
    "tweet_thread": 0.005, "tweet_replies": 0.001, "user_info": 0.001,
}

CAP_DEFAULT = 0.50


def _key() -> str:
    p = Path("/tmp/opencode/getx.key")
    if p.exists():
        return p.read_text().strip()
    return os.environ.get("GETXAPI_KEY", "")


def _state() -> dict:
    try:
        return json.loads(BUDGET.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"spent": 0.0, "calls": 0, "cap": CAP_DEFAULT}


def _save(state: dict) -> None:
    BUDGET.parent.mkdir(parents=True, exist_ok=True)
    BUDGET.write_text(json.dumps(state, indent=1), encoding="utf-8")


def spend_ok(cost: float, cap: float | None = None) -> bool:
    s = _state()
    return s["spent"] + cost <= (cap if cap is not None else s.get("cap", CAP_DEFAULT))


def _log(endpoint: str, cost: float, tweets: int = 0) -> None:
    s = _state()
    s["spent"] = round(s.get("spent", 0.0) + cost, 4)
    s["calls"] = s.get("calls", 0) + 1
    _save(s)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                            "endpoint": endpoint, "cost": cost,
                            "tweets": tweets,
                            "session_spent": s["spent"]}) + "\n")


_LAST = [0.0]


def call(endpoint: str, params: dict, timeout: int = 30) -> dict | None:
    """One metered call. Returns None on budget block or failure."""
    key = endpoint.split("/")[-1]
    cost = COSTS.get(key, 0.001)
    if not spend_ok(cost):
        return None
    el = time.time() - _LAST[0]
    if el < 2.1:
        time.sleep(2.1 - el)
    try:
        url = f"{BASE}{endpoint}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {_key()}"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8", "replace"))
        _LAST[0] = time.time()
        n = len(doc.get("tweets", []) or [])
        _log(key, cost, n)
        return doc
    except Exception:
        return None


def status() -> dict:
    s = _state()
    return {"spent": s.get("spent", 0.0), "calls": s.get("calls", 0),
            "cap": s.get("cap", CAP_DEFAULT)}
