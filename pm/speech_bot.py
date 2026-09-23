"""E8 speech-count bot — deterministic word counting per the Polymarket
Event Mentions contract, wired to the paper book.

Contract rules implemented (Event Mentions Contract DeFi):
  - spoken during the NAMED event only; Q&A counts; aired clips count
  - plural + possessive qualify ("Immigrant" <- "Immigrants", "Russia" <- "Russia's")
  - a SPECIFIED plural excludes the singular ("Veterans" <- not "Veteran")
  - plural-spelled homographs excluded ("Wind" <- not "winds up the clock")
  - tense/conjugation/derivation excluded ("Run" <- not "Running"/"Ran")
  - adjective-only: only the adjective form ("economic" <- not "economics")
  - compounds qualify across spaces and hyphens ("fire" <- "fire station")
  - digits spoken as words qualify as written, not as a larger numeral
    ("5" <- "five", but NOT "five hundred")
  - ordinals: "3" <- "3rd"/"third"; cardinal and ordinal are distinct
    ("one" <- not "first")
  - on-screen-only text, muting/censorship, phonetic spelling: never counts

Subcommands:
  scan    discover live word-count families, parse legs, flag fade candidates
  count   fetch the event transcript, count terms, emit per-leg verdicts
  paper   convert verdicts into paper-book entries (appends, never signs)
  status  one-line summary of armed families and open verdicts

Usage:
    python3 pm/speech_bot.py scan
    python3 pm/speech_bot.py count --event "State Arrival Ceremony"
    python3 pm/speech_bot.py status
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"
WHITEHOUSE = "https://www.whitehouse.gov/remarks/"
STATE = ROOT / "data" / "engine" / "speech_state.json"
VERDICTS = ROOT / "data" / "engine" / "speech_verdicts.jsonl"
PAPER = ROOT / "data" / "paper" / "positions.jsonl"

FADE_MULT = 4.0
FADE_FLOOR = 0.05
YES_CEIL = 0.90
SEARCH_QS = [
    "Trump say", "Biden say", "State of the Union", "remarks at",
    "press conference", "address", "interview", "say this week",
    "say this month", "inaugural", "debate", "speech",
]

DIGITS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
          "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
          "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
          "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
          "18": "eighteen", "19": "nineteen", "20": "twenty", "30": "thirty",
          "40": "forty", "50": "fifty", "60": "sixty", "70": "seventy",
          "80": "eighty", "90": "ninety"}
ORDINALS = {"1": "first", "2": "second", "3": "third", "4": "fourth",
            "5": "fifth", "6": "sixth", "7": "seventh", "8": "eighth",
            "9": "ninth", "10": "tenth"}
SCALE_WORDS = {"hundred", "thousand", "million", "billion", "trillion"}
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
ADJECTIVE_ONLY = {"economic", "democratic", "republican", "magic", "historic",
                  "robotic", "electric", "nuclear", "federal", "presidential",
                  "constitutional", "military", "diplomatic", "autocratic"}


def get_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "predict-speech"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


# ---------------------------------------------------------------- parsing

def parse_leg(question: str) -> dict:
    """Question -> {terms, threshold, mode}. Deterministic, no guessing:
    unparsed shapes return mode='unknown' and are skipped by the bot."""
    q = question.strip()
    terms = re.findall(r'"([^"]+)"', q)
    if not terms:
        return {"terms": [], "mode": "unknown"}
    m = re.search(r"(\d+)\s*\+?\s*times", q, re.I)
    if m:
        return {"terms": terms, "threshold": int(m.group(1)), "mode": "count"}
    if re.search(r"\bfirst\b", q, re.I):
        return {"terms": terms, "threshold": 1, "mode": "first"}
    return {"terms": terms, "threshold": 1, "mode": "presence"}


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower().replace("-", " "))


def term_forms(term: str) -> tuple[set[str], set[str]]:
    """(plural-tolerant forms, strict forms).

    Contract: plural/possessive of the word qualify; a word specified in
    plural excludes the singular; derivations/tenses never qualify;
    adjective-only words have no qualifying plural ("economics" is not a
    mention of "economic"). Strict forms = the word as written plus its
    possessive, so a verdict that depends on plurals is separable.
    """
    t = term.lower().strip()
    if t.endswith("'s"):
        t = t[:-2]
    if t in DIGITS:
        strict = {DIGITS[t]}
        if t in ORDINALS:
            strict.add(ORDINALS[t])
    elif t in ORDINALS:
        strict = {t}
    else:
        strict = {t}
    strict.add(t + "'s")
    forms = set(strict)
    specified_plural = bool(t.endswith("s") and not t.endswith("ss"))
    if not specified_plural and t not in ADJECTIVE_ONLY:
        forms.add(t + "s")
    return forms, strict


def count_term(tokens: list[str], term: str) -> tuple[int, int]:
    """(plural-tolerant count, strict count) of contract-qualifying mentions."""
    forms, strict = term_forms(term)
    loose = strict_count = 0
    for i, tok in enumerate(tokens):
        if tok in forms:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if nxt in SCALE_WORDS:
                continue  # "five hundred" is a larger numeral, not a mention of "5"
            loose += 1
            if tok in strict:
                strict_count += 1
    return loose, strict_count


def verdict_for(leg: dict, text: str) -> dict:
    tokens = tokenize(text)
    counts = {t: dict(zip(("loose", "strict"), count_term(tokens, t)))
              for t in leg["terms"]}
    loose_total = sum(c["loose"] for c in counts.values())
    strict_total = sum(c["strict"] for c in counts.values())
    threshold = leg.get("threshold", 1)
    if leg.get("mode") == "count":
        said = loose_total >= threshold
        sure = strict_total >= threshold
    else:
        said = loose_total > 0
        sure = strict_total > 0
    return {"counts": counts, "total": loose_total, "strict_total": strict_total,
            "says_yes": said, "says_yes_strict": sure,
            "plural_only": bool(said and not sure), "words": len(tokens)}


# ---------------------------------------------------------------- families

def discover() -> dict:
    fams: dict = {}
    seen: set = set()
    for q in SEARCH_QS:
        url = f"{GAMMA}/public-search?" + urllib.parse.urlencode({"q": q, "limit_tag": 6})
        try:
            doc = get_json(url)
        except Exception as e:
            print(f"  [{q}] ERR {str(e)[:60]}")
            continue
        for ev in (doc if isinstance(doc, list) else doc.get("events", [])):
            legs = []
            for m in (ev.get("markets") or []):
                qn = (m.get("question") or "")
                if "say" not in qn.lower() or qn in seen:
                    continue
                if (m.get("umaResolutionStatus") or "").lower() in ("resolved", "finalized"):
                    continue
                if m.get("active") is False:
                    continue
                try:
                    p = float(json.loads(m.get("outcomePrices") or "[]")[0])
                except (ValueError, TypeError, IndexError):
                    continue
                parsed = parse_leg(qn)
                if parsed["mode"] == "unknown":
                    continue
                seen.add(qn)
                legs.append({**parsed, "q": qn, "p_yes": p,
                             "bid": m.get("bestBid"), "ask": m.get("bestAsk"),
                             "end": (m.get("endDate") or "")[:10],
                             "vol": float(m.get("volume") or 0),
                             "liq": float(m.get("liquidity") or 0),
                             "cid": m.get("conditionId")})
            if len(legs) >= 8:
                fams[f"{ev.get('title', '')[:60]}"] = {
                    "title": ev.get("title", ""), "legs": legs}
        time.sleep(0.7)
    return fams


def screen(legs: list[dict]) -> dict:
    prices = [l["p_yes"] for l in legs]
    med = statistics.median(prices)
    thr = max(FADE_FLOOR, med * FADE_MULT, med + FADE_FLOOR)
    for l in legs:
        l["fade_thr"] = round(thr, 4)
        l["family_med"] = round(med, 4)
        l["fade_candidate"] = bool(l["p_yes"] >= thr and (1 - l["p_yes"]) >= 0.05)
    return {"median": round(med, 4), "threshold": round(thr, 4), "n": len(legs)}


# ---------------------------------------------------------------- transcript

STOPWORDS = {"will", "say", "say", "says", "said", "during", "the", "at",
             "and", "or", "a", "an", "in", "of", "his", "her", "their",
             "remarks", "this", "week", "month", "what", "this", "mentions"}


def find_transcript(fam: dict) -> tuple[str, str]:
    """Return (url, raw_text) for the transcript that provably belongs to
    this family. Two hard gates: the page URL must carry the event's own
    year/month, and a majority of the family's distinctive title words must
    appear on the page. A loose match is worse than no match — a wrong
    transcript fabricates every word count in the family."""
    event_date = (fam.get("legs") or [{}])[0].get("end") or ""
    if len(event_date) < 7:
        return "", ""
    ym = f"/{event_date[:4]}/{event_date[5:7]}/"
    title = (fam.get("title") or "").lower()
    hints = [w for w in re.findall(r"[a-z]+", title)
             if len(w) > 3 and w not in STOPWORDS]
    if not hints:
        return "", ""
    try:
        idx = get_text(WHITEHOUSE)
    except Exception as e:
        print(f"  index ERR {str(e)[:50]}")
        return "", ""
    links = [l for l in dict.fromkeys(
        re.findall(r'href="(https://www\.whitehouse\.gov/remarks/[^"]+)"', idx))
        if ym in l]
    for link in links:
        try:
            page = get_text(link)
        except Exception:
            continue
        low = page.lower()
        hits = sum(h in low for h in hints)
        if hits >= max(2, (len(hints) * 3) // 5):
            body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
            body = re.sub(r"<[^>]+>", " ", body)
            return link, re.sub(r"\s+", " ", body)
    return "", ""


# ---------------------------------------------------------------- commands

def cmd_scan(args) -> int:
    fams = discover()
    state = {"ran_at": datetime.now(timezone.utc).isoformat(), "families": {}}
    for name, fam in fams.items():
        sc = screen(fam["legs"])
        state["families"][name] = {**fam, **sc}
        print(f"{name[:56]:58} legs={sc['n']:3} med={sc['median']:.3f} thr={sc['threshold']:.3f} "
              f"fades={sum(l['fade_candidate'] for l in fam['legs'])}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))
    print(f"[SAVED] {STATE.relative_to(ROOT)} families={len(state['families'])}")
    return 0


def cmd_count(args) -> int:
    state = json.loads(STATE.read_text()) if STATE.exists() else {"families": {}}
    targets = [n for n in state["families"]
               if not args.event or args.event.lower() in n.lower()]
    if not targets:
        print("no armed families; run scan first")
        return 1
    for name in targets:
        fam = state["families"][name]
        print(f"[FAMILY] {name} (ends {fam['legs'][0]['end']})")
        url, text = ("inline", args.text) if args.text else find_transcript(fam)
        if not text:
            print("  no date-matched transcript — event not published, or gate refused")
            continue
        print(f"  transcript: {url} ({len(text)} chars)")
        for leg in fam["legs"]:
            v = verdict_for(leg, text)
            side, why = None, ""
            if v["says_yes_strict"] and leg["p_yes"] <= YES_CEIL:
                side = "YES"
                why = f"transcript confirms {v['strict_total']} strict mention(s)"
            elif leg["fade_candidate"] and not v["says_yes"]:
                side = "NO"
                why = (f"zero mentions; narrative premium {leg['p_yes']:.3f} "
                       f">= {leg['fade_thr']:.3f} family threshold")
            elif v["plural_only"]:
                why = ("plural-only mention(s), homograph risk — review, not auto-traded")
            row = {"at": datetime.now(timezone.utc).isoformat(), "family": name,
                   "question": leg["q"], "cid": leg["cid"], "p_yes": leg["p_yes"],
                   "verdict": v, "action": side, "why": why,
                   "transcript": url, "transcript_ok": bool(url),
                   "threshold": leg.get("threshold"), "mode": leg.get("mode")}
            with open(VERDICTS, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            if side or why:
                tag = side or "REVIEW"
                print(f"  {tag:7} p={leg['p_yes']:.3f} {v['total']:3}x/{v['strict_total']:3}strict "
                      f"{leg['q'][:46]} — {why}")
    print(f"[SAVED] {VERDICTS.relative_to(ROOT)}")
    return 0


def cmd_paper(args) -> int:
    if not VERDICTS.exists():
        print("no verdicts yet")
        return 1
    rows = [json.loads(l) for l in VERDICTS.read_text().splitlines() if l.strip()]
    if args.since:
        rows = [r for r in rows if r["at"] >= args.since]
    logged = set()
    if PAPER.exists():
        logged = {(json.loads(l).get("family"), json.loads(l).get("question"))
                  for l in PAPER.read_text().splitlines() if l.strip()}
    n = 0
    for r in rows:
        if not r.get("action"):
            continue
        if not r.get("transcript_ok"):
            continue  # unverified transcript source never reaches the book
        key = (r["family"], r["question"])
        if key in logged:
            continue
        model_p = 1.0 if r["action"] == "YES" else 0.0
        entry = {"slug": f"speech::{r['family'][:40]}", "question": r["question"],
                 "judge": "contract-counter", "model_p": model_p,
                 "market_p": r["p_yes"], "edge": round(abs(model_p - r["p_yes"]), 4),
                 "confidence": 0.95, "units": 1,
                 "at": r["at"], "why": r["why"]}
        with open(PAPER, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        logged.add(key)
        n += 1
    print(f"[PAPER] {n} entr{'y' if n == 1 else 'ies'} appended (confidence 0.95, 1 unit, no keys touched)")
    return 0


def cmd_status(args) -> int:
    if not STATE.exists():
        print("no state; run scan")
        return 1
    state = json.loads(STATE.read_text())
    print(f"armed families: {len(state['families'])} (scanned {state['ran_at']})")
    for name, fam in state["families"].items():
        fades = sum(l["fade_candidate"] for l in fam["legs"])
        print(f"  {name[:52]:54} legs={fam['n']:3} med={fam['median']:.3f} fades={fades}")
    if VERDICTS.exists():
        rows = [json.loads(l) for l in VERDICTS.read_text().splitlines() if l.strip()]
        acted = [r for r in rows if r.get("action")]
        print(f"verdicts: {len(rows)} ({len(acted)} actionable)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    c = sub.add_parser("count")
    c.add_argument("--event", default="")
    c.add_argument("--text", default="")
    p = sub.add_parser("paper")
    p.add_argument("--since", default="")
    sub.add_parser("status")
    args = ap.parse_args()
    return {"scan": cmd_scan, "count": cmd_count, "paper": cmd_paper,
            "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
