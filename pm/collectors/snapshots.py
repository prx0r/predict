"""Market snapshots — immutable, fully-resolved market reads.

Boundary rule (peer-review P0 fix): ALL network I/O happens here, in the
collectors layer. Evaluators (`killfeed.evaluate`, `pm_reading`) accept
snapshots and import no collector modules. A snapshot carries price,
spread, depth, timestamp and a source hash; evaluation is a pure function
of snapshots and can be tested with sockets disabled.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request

UA = {"User-Agent": "bneck"}


def _get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def snapshot_market(m: dict, ts: str = "") -> dict:
    """Resolve one market row into an immutable snapshot (does I/O)."""
    import time as _t
    snap = {"question": (m.get("question") or "")[:160],
            "p": float(m.get("p", 0.0)),
            "volume": float(m.get("volume", 0)),
            "liquidity": float(m.get("liquidity", 0)),
            "tier": m.get("tier") or "low-liquidity",
            "venue": m.get("venue", "?"),
            "conditionId": m.get("conditionId") or "",
            "depth_top5": 0.0, "spread": None,
            "ts": ts or _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime())}
    if snap["venue"] == "polymarket" and snap["conditionId"]:
        try:
            from collectors import clob as _CLOB
            det = _get_json("https://gamma-api.polymarket.com/markets?condition_id="
                            + snap["conditionId"])
            tids = json.loads((det[0].get("clobTokenIds") or "[]")) if det else []
            if tids:
                book = _CLOB.book(str(tids[0]))
                snap["depth_top5"] = float(book.get("depth_top5", 0) or 0)
                snap["spread"] = book.get("spread")
        except Exception:
            pass
    blob = json.dumps({k: snap[k] for k in sorted(snap) if k != "ts"},
                      sort_keys=True)
    snap["source_hash"] = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return snap


def snapshot_all(markets: list[dict], limit: int = 3,
                 sleep_s: float = 0.5) -> list[dict]:
    """Snapshot the top-`limit` markets by book size (bounded I/O)."""
    ranked = sorted(markets,
                    key=lambda m: (float(m.get("liquidity", 0)),
                                   float(m.get("volume", 0))),
                    reverse=True)[:max(limit, 0)]
    out = []
    for m in ranked:
        out.append(snapshot_market(m))
        time.sleep(sleep_s)
    return out
