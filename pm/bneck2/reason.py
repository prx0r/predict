"""Reasoning bandit — 6 lenses for proposing variables (REFeat pattern).

Arms: inductive / deductive / abductive / analogical / counterfactual /
causal. Each arm carries pulls + reward_sum in data/lab/bandit.json.
pick(): Boltzmann sample (temperature 1.0). record(): update from
validation gain. The agent consults pick() before proposing; receipts
record which arm sired each variable.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "lab" / "bandit.json"

ARMS = ("inductive", "deductive", "abductive", "analogical",
        "counterfactual", "causal")

PROMPTS = {
    "inductive": "Examine these examples and hypothesize a variable that distinguishes outcomes based on observed patterns: {context}",
    "deductive": "From the thesis premises, derive a variable that MUST co-move if the theory holds: {context}",
    "abductive": "Given this surprising result, what hidden variable would best explain it? {context}",
    "analogical": "What analogous system has a measured variable we lack here? Port it: {context}",
    "counterfactual": "In worlds where the outcome flips, what variable differs? Measure that: {context}",
    "causal": "What intervention would move the target? The manipulable lever is the variable: {context}",
}


def load() -> dict:
    try:
        doc = json.loads(STATE.read_text(encoding="utf-8"))
        for a in ARMS:
            doc.setdefault(a, {"pulls": 0, "reward": 0.0})
        return doc
    except (OSError, ValueError):
        return {a: {"pulls": 0, "reward": 0.0} for a in ARMS}


def save(doc: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(doc, indent=1), encoding="utf-8")


def means(doc: dict) -> dict[str, float]:
    return {a: (doc[a]["reward"] / doc[a]["pulls"] if doc[a]["pulls"] else 0.0)
            for a in ARMS}


def pick(doc: dict | None = None, temperature: float = 1.0,
         seed: int | None = None) -> str:
    """Boltzmann-sample an arm by mean reward (uniform at start)."""
    doc = doc if doc is not None else load()
    rng = random.Random(seed)
    ms = means(doc)
    ws = {a: math.exp(ms[a] / temperature) for a in ARMS}
    tot = sum(ws.values())
    x = rng.random() * tot
    for a in ARMS:
        x -= ws[a]
        if x <= 0:
            return a
    return ARMS[-1]


def record(arm: str, reward: float, doc: dict | None = None) -> dict:
    doc = doc if doc is not None else load()
    if arm in doc:
        doc[arm]["pulls"] += 1
        doc[arm]["reward"] += float(reward)
    save(doc)
    return doc
