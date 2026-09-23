"""Judge interface — how Jev (or any LLM) prices a structured record.

The engine never judges. It builds the prompt from the record, and the
judge returns model_p + rationale + key uncertainties, which the engine
logs with judge identity + version. Swap judges without touching the
engine; compare judges on Brier over time.

Prompt contract (what Jev receives):
  - question, market_p, book state, deadline
  - requirements[], exclusions[], timing, source
  - alpha precedents + crux (if researched)
  - instruction: return a number, a range, rationale, uncertainties.

Response contract (what gets logged):
  {model_p, low_p, high_p, rationale, uncertainties[], judge, judge_version}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


def build_prompt(rec: dict) -> str:
    lines = [
        f"MARKET: {rec.get('question')}",
        f"Market price (Yes): {rec.get('market_p')}",
        f"Book: bid {rec.get('bestBid')} / ask {rec.get('bestAsk')}, "
        f"volume ${rec.get('volume', 0):,.0f}, liquidity ${rec.get('liquidity', 0):,.0f}",
        f"Deadline: {rec.get('endDate')}",
        "",
        "REQUIREMENTS (all must hold for Yes):",
    ]
    for s in rec.get("requirements", []):
        lines.append(f"  - {s[:220]}")
    lines.append("EXCLUSIONS (these do NOT count):")
    for s in rec.get("exclusions", []):
        lines.append(f"  - {s[:220]}")
    alpha = rec.get("alpha") or {}
    if alpha.get("precedents"):
        lines.append("RESEARCHED PRECEDENTS:")
        for p in alpha["precedents"]:
            lines.append(f"  - {p[:220]}")
    if alpha.get("crux"):
        lines.append(f"CRUX: {alpha['crux'][:300]}")
    lines += [
        "",
        "TASK: estimate P(Yes). Return JSON only:",
        '{"model_p": <0-1>, "low_p": <0-1>, "high_p": <0-1>, '
        '"rationale": "<2 sentences>", "uncertainties": ["...", "..."]}',
        "Rules: title implies nothing — price ONLY what the conditions, "
        "as written, will resolve to. State base rates explicitly.",
    ]
    return "\n".join(lines)


def record_judgment(rec: dict, judgment: dict, judge: str,
                    judge_version: str = "v1") -> dict:
    """Attach a judgment to a record copy. Never mutates history in place
    semantics: caller saves as a new revision (corrections are new entries)."""
    out = dict(rec)
    out["model_p"] = judgment.get("model_p")
    out["low_p"] = judgment.get("low_p")
    out["high_p"] = judgment.get("high_p")
    out["model_rationale"] = judgment.get("rationale")
    out["uncertainties"] = judgment.get("uncertainties", [])
    out["judge"] = judge
    out["judge_version"] = judge_version
    out["model_at"] = datetime.now(timezone.utc).isoformat()
    mp, mk = out["model_p"], rec.get("market_p")
    out["edge"] = round(mp - mk, 3) if isinstance(mp, (int, float)) and isinstance(mk, (int, float)) else None
    out["status"] = "assessed"
    return out


def jev_decide(state, questions, model="typesafe/jev-1.13",
               api_key=None, timeout=90):
    """Call Jev via OpenRouter Decisions API (typed noul/choice/score).

    Key NEVER stored: pass api_key at runtime (env OPENROUTER_API_KEY).
    Returns the answers dict. $0.042/M input, outputs free.
    Endpoint: POST https://openrouter.ai/api/alpha/decisions
    """
    import os
    import urllib.request
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise ValueError("no API key (env OPENROUTER_API_KEY)")
    body = json.dumps({"model": model, "state": state,
                       "questions": questions}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/alpha/decisions", data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r).get("answers", {})


if __name__ == "__main__":
    import sys
    from pathlib import Path
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    rec = json.loads(Path(p).read_text()) if p else {"question": "demo"}
    print(build_prompt(rec)[:800])
