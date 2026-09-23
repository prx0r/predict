"""Monthly panel sampler + E049 horse race (stdlib only).

Reads data/hf_panel/daily.jsonl (symbol, month-end adj_close), builds
monthly L/S factor tests: mom12_1, bounce36, lowvol12. Train 2016-2020
picks the factor; test 2021-2026-07 judges once vs buy-hold.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "hf_panel" / "monthly.jsonl"


def build_monthly() -> dict:
    by_sym: dict[str, dict[str, float]] = {}
    for line in (ROOT / "data" / "hf_panel" / "daily.jsonl").open():
        r = json.loads(line)
        by_sym.setdefault(r["s"], {})[r["d"][:7]] = r["c"]
    n = 0
    with PANEL.open("w") as f:
        for s, m in sorted(by_sym.items()):
            for ym in sorted(m):
                f.write(json.dumps({"s": s, "m": ym, "c": m[ym]}) + "\n")
                n += 1
    return {"months_written": n, "symbols": len(by_sym)}


def load() -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    for line in PANEL.open():
        r = json.loads(line)
        out.setdefault(r["s"], []).append((r["m"], r["c"]))
    for s in out:
        out[s].sort()
    return out


def month_idx(panel: dict, s: str) -> dict[str, int]:
    return {m: i for i, (m, _) in enumerate(panel[s])}


def signal(panel, s: str, i: int, mode: str):
    px = [c for _, c in panel[s]]
    if mode == "mom12_1":
        if i < 13 or not px[i - 13]:
            return None
        return (px[i - 1] - px[i - 13]) / px[i - 13]
    if mode == "bounce36":
        win = px[max(i - 36, 0):i + 1]
        if len(win) < 24 or not min(win):
            return None
        return -((px[i] - min(win)) / min(win))
    if mode == "lowvol":
        win = px[max(i - 12, 0):i + 1]
        if len(win) < 12:
            return None
        rets = [(win[k] - win[k - 1]) / win[k - 1] for k in range(1, len(win)) if win[k - 1]]
        if not rets:
            return None
        mu = sum(rets) / len(rets)
        var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)
        return -math.sqrt(var) if var > 0 else None
    return None


def run_panel(panel, months: list[str], mode: str, q: float = 0.2) -> dict:
    rets = []
    for mi, m in enumerate(months):
        scored = []
        for s, series in panel.items():
            idx = {mm: k for k, (mm, _) in enumerate(series)}
            if m not in idx:
                continue
            i = idx[m]
            sig = signal(panel, s, i, mode)
            if sig is None:
                continue
            if i + 1 >= len(series):
                continue
            c0, c1 = series[i][1], series[i + 1][1]
            if not c0:
                continue
            scored.append((sig, (c1 - c0) / c0))
        if len(scored) < 10:
            continue
        scored.sort()
        k = max(int(len(scored) * q), 1)
        longs = [r for _, r in scored[-k:]]
        shorts = [r for _, r in scored[:k]]
        rets.append(sum(longs) / len(longs) - sum(shorts) / len(shorts))
    n = len(rets)
    if n < 12:
        return {"sharpe": None, "n": n}
    mu = sum(rets) / n
    var = sum((x - mu) ** 2 for x in rets) / (n - 1)
    sh = (mu * 12) / math.sqrt(var * 12) if var > 0 else 0.0
    tot = 1.0
    for x in rets:
        tot *= 1 + x
    return {"sharpe": round(sh, 3), "total": round(tot - 1, 3), "n": n}


def buyhold(panel, months: list[str]) -> dict:
    rets = []
    for m in months:
        rs = []
        for s, series in panel.items():
            idx = {mm: k for k, (mm, _) in enumerate(series)}
            if m not in idx or idx[m] + 1 >= len(series):
                continue
            i = idx[m]
            if series[i][1]:
                rs.append((series[i + 1][1] - series[i][1]) / series[i][1])
        if rs:
            rets.append(sum(rs) / len(rs))
    n = len(rets)
    mu = sum(rets) / n
    var = sum((x - mu) ** 2 for x in rets) / (n - 1)
    sh = (mu * 12) / math.sqrt(var * 12) if var > 0 else 0.0
    return {"sharpe": round(sh, 3), "n": n}


def main() -> dict:
    if not PANEL.exists():
        print(json.dumps(build_monthly()))
    panel = load()
    syms = [s for s, v in panel.items() if len(v) >= 100]
    panel = {s: panel[s] for s in syms}
    all_m = sorted({m for v in panel.values() for m, _ in v})
    train = [m for m in all_m if "2016-01" <= m <= "2020-12"]
    test = [m for m in all_m if "2021-01" <= m <= "2026-07"]
    tune = {m: run_panel(panel, train, m)["sharpe"] for m in ("mom12_1", "bounce36", "lowvol")}
    tune = {k: v for k, v in tune.items() if v is not None}
    best = max(tune, key=lambda k: tune[k])
    out = {"tune": tune, "best": best,
           best: run_panel(panel, test, best),
           "buyhold": buyhold(panel, test),
           "symbols": len(panel), "test_months": len(test)}
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
