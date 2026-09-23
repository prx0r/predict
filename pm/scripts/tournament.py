#!/usr/bin/env python3
"""Tournament runner — identical screens for all seeds, results logged.

Usage: /usr/bin/python3 scripts/tournament.py <round> [--mutate-from <prev>]
Round dir: data/tournament/<round>/{seeds.json,results.json,mutations.json}.
Seeds file lists factors; screening uses the biweekly panel (train/holdout
split built in). Mutations derive seed1.1 from round results + justifications.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TDIR = ROOT / "data" / "tournament"


def load_panel() -> list[dict]:
    rows = []
    for f in sorted((ROOT / "data" / "predict").glob("biwk-*.jsonl")):
        rows += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    return [r for r in rows if r.get("fwd_20") is not None]


def screen_seed(rows: list[dict], factor: str) -> dict:
    from bneck2 import predict as PD
    xs = [r.get(factor) for r in rows]
    ys = [r.get("fwd_20") for r in rows]
    ic = PD.spearman(xs, ys)
    n = sum(1 for x, y in zip(xs, ys) if x is not None and y is not None)
    return {"factor": factor, "IC": ic, "n": n}


SEED1 = [
    {"id": "seed1.mom", "factor": "f_mom_20"},
    {"id": "seed1.burst", "factor": "f_burst"},
    {"id": "seed1.attack", "factor": "f_attack"},
    {"id": "seed1.hn", "factor": "f_hn"},
    {"id": "seed1.short", "factor": "f_short"},
    {"id": "seed1.conv", "factor": "f_conv"},
    {"id": "seed1.B", "factor": "f_B"},
]


def mutate(prev: dict) -> tuple[list[dict], list[dict]]:
    """seed1.1: keep sign-stable promotables, drop failures, add one
    interaction child per surviving family (documented why)."""
    seeds, mutations = [], []
    for s in prev["seeds"]:
        if s["verdict"] == "PROMOTE":
            seeds.append({"id": s["id"].replace("seed1", "seed1.1"),
                          "factor": s["factor"], "parent": s["id"]})
            mutations.append({"op": "keep", "id": s["id"],
                              "why": f"train {s['train_IC']} hold {s['hold_IC']} same sign"})
        else:
            mutations.append({"op": "drop", "id": s["id"],
                              "why": f"train {s['train_IC']} hold {s['hold_IC']} unstable/absent"})
    # one child: momentum × attack interaction (both survived before)
    fams = {s["factor"] for s in prev["seeds"] if s["verdict"] == "PROMOTE"}
    if "f_mom_20" in fams and "f_attack" in fams:
        seeds.append({"id": "seed1.1.mom_x_attack", "factor": "f_mom_x_attack",
                      "parent": "seed1.mom+seed1.attack"})
        mutations.append({"op": "add-interaction", "id": "seed1.1.mom_x_attack",
                          "why": "both parents promoted; test joint over marginal"})
    return seeds, mutations


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "r1"
    d = TDIR / name
    d.mkdir(parents=True, exist_ok=True)
    if "--mutate-from" in sys.argv:
        prev_name = sys.argv[sys.argv.index("--mutate-from") + 1]
        prev = json.loads((TDIR / prev_name / "results.json").read_text())
        seeds, mutations = mutate(prev)
        (d / "mutations.json").write_text(json.dumps(mutations, indent=1))
    else:
        seeds = SEED1
    (d / "seeds.json").write_text(json.dumps(seeds, indent=1))
    # interaction factor support
    results = run_round_with_factors(name, seeds)
    (d / "results.json").write_text(json.dumps(results, indent=1))
    print(f"round {name}: " +
          ", ".join(f"{s['id']}={s['verdict']}" for s in results["seeds"]))
    return 0


def run_round_with_factors(name: str, seeds: list[dict]) -> dict:
    from bneck2 import predict as PD
    rows = load_panel()
    dates = sorted({r["date"] for r in rows})
    cut = dates[max(len(dates) - 8, 0)]
    train = [r for r in rows if r["date"] < cut]
    hold = [r for r in rows if r["date"] >= cut]

    def feat(r, f):
        if f == "f_mom_x_attack":
            a, b = r.get("f_mom_20"), r.get("f_attack")
            return a * b if a is not None and b is not None else None
        return r.get(f)

    out = {"round": name, "n_train": len(train), "n_hold": len(hold), "seeds": []}
    from bneck2 import lab as LAB
    for s in seeds:
        tri = screen_seed([{**r, "_v": feat(r, s["factor"])} for r in train],
                          "_v")
        hoi = screen_seed([{**r, "_v": feat(r, s["factor"])} for r in hold],
                          "_v")
        v = (tri["IC"], hoi["IC"])
        verdict = ("PROMOTE" if v[0] is not None and v[1] is not None
                   and abs(v[0]) > 0.1 and abs(v[1]) > 0.1
                   and (v[0] > 0) == (v[1] > 0) else "DEMOTE")
        out["seeds"].append({"id": s["id"], "factor": s["factor"],
                             "parent": s.get("parent"),
                             "train_IC": v[0], "hold_IC": v[1],
                             "verdict": verdict})
        LAB.alog(f"A-TOURN-{name}",
                 f"{s['id']} {s['factor']}: train {v[0]} hold {v[1]} -> {verdict}")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
