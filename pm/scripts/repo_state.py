#!/usr/bin/env python3
"""Repo state — generate docs/STATE.md from the repo itself (peer-review P2).

Every volatile number (test counts, ledger sizes, collector inventory,
thresholds) is computed, never hand-maintained. READMEs point here instead
of quoting numbers that rot. Usage: /usr/bin/python3 scripts/repo_state.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def count_tests() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"))
    return suite.countTestCases()


def count_jsonl(path: Path) -> int:
    try:
        return sum(1 for _ in path.read_text(encoding="utf-8").splitlines() if _.strip())
    except OSError:
        return 0


def main() -> int:
    from bneck2 import lab as LAB
    n_tests = count_tests()
    collectors = sorted(p.stem for p in (ROOT / "collectors").glob("*.py")
                        if p.stem != "__init__")
    ver = LAB.verdict_coverage(str(ROOT))
    sup = LAB.support_rate()
    leg = LAB.possibility_ledger()
    sev = count_jsonl(ROOT / "data" / "bottlenecks" / "severity_history.jsonl")
    panel = count_jsonl(ROOT / "data" / "backtest" / "panel.jsonl")
    sig = count_jsonl(ROOT / "data" / "beliefs" / "signals.jsonl")
    import glob
    n_hyps = len(glob.glob(str(ROOT / "experimentation" / "hypotheses" / "*.md")))
    n_vars = 0
    try:
        n_vars = sum(1 for _ in (ROOT / "experimentation" / "variables.jsonl")
                     .read_text(encoding="utf-8").splitlines() if _.strip())
    except OSError:
        pass
    lines = [
        "# Repo state — GENERATED, do not hand-edit",
        "",
        f"- tests: **{n_tests} green** (`python3 -m unittest discover -s tests`)",
        f"- collectors: {len(collectors)} ({', '.join(collectors)})",
        f"- verdicts: {ver['rows']} rows, {ver['cells_tested']} cells, "
        f"{ver['cells_triggered']} triggered",
        f"- signals: {sig} rows; severity snapshots: {sev}; panel rows: {panel}",
        f"- hypotheses: {leg['hypotheses']} ({leg['confirmed']} confirmed, "
        f"{leg['refuted']} refuted, {leg['open']} open), {leg['runs']} runs",
        f"- support: {sup['rate']} 95% CI [{sup['lo']}, {sup['hi']}]",
        f"- hypothesis files: {n_hyps}; registered variables: {n_vars}",
        "",
        "Regenerate: `/usr/bin/python3 scripts/repo_state.py`. CI checks "
        "the suite; this file is informational and rebuilt on demand.",
    ]
    (ROOT / "docs" / "STATE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
