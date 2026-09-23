"""bneck patents — capability->technique->claim->owner FTO mapping.

Not "company owns N patents" (useless). Instead:
  require(capability, technique)      what an implementation needs
  cover(technique, family, owner)     which claims blanket it
  substitute(technique, alternative)  escape routes
  legal_chokepoint(company, architectures)
      = share of viable architectures whose EVERY performant path
        traverses company-owned families. 11 archs, 10 route around ->
        not a bottleneck. Frontier converges through your claims -> tollbooth.

Plus CRISPR-style precedent records: patents didn't stop science, they
decided who captured rents. Stdlib only. Store: data/patents/fto.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FTO_PATH = ROOT / "data" / "patents" / "fto.json"


def new_map() -> dict:
    return {"requires": {}, "covers": {}, "substitutes": {}, "architectures": {}}


def load_map(path: Path = FTO_PATH) -> dict:
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
        for k in ("requires", "covers", "substitutes", "architectures"):
            m.setdefault(k, {})
        return m
    except (OSError, ValueError):
        return new_map()


def save_map(m: dict, path: Path = FTO_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, indent=1), encoding="utf-8")


def require(m: dict, capability: str, technique: str) -> dict:
    m["requires"].setdefault(capability, [])
    if technique not in m["requires"][capability]:
        m["requires"][capability].append(technique)
    return m


def cover(m: dict, technique: str, family: str, owner: str) -> dict:
    m["covers"].setdefault(technique, [])
    if [family, owner] not in m["covers"][technique]:
        m["covers"][technique].append([family, owner])
    return m


def substitute(m: dict, technique: str, alternative: str) -> dict:
    m["substitutes"].setdefault(technique, [])
    if alternative not in m["substitutes"][technique]:
        m["substitutes"][technique].append(alternative)
    return m


def legal_chokepoint(m: dict, company: str) -> dict:
    """For each architecture (technique set), does EVERY technique have at
    least one company-owned family with no listed substitute? Share = toll."""
    archs = m.get("architectures", {})
    if not archs:
        return {"company": company, "architectures": 0, "blocked": 0, "share": 0.0}
    blocked = 0
    for techs in archs.values():
        trapped = True
        for t in techs:
            fams = [o for _, o in m.get("covers", {}).get(t, [])]
            subs = m.get("substitutes", {}).get(t, [])
            if company not in fams or subs:
                trapped = False
                break
        blocked += trapped
    return {"company": company, "architectures": len(archs), "blocked": blocked,
            "share": round(blocked / len(archs), 3)}
