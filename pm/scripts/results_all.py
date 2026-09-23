#!/usr/bin/env python3
"""Results ledger — rebuild docs/RESULTS-ALL.md purely from receipts.

Projection rule: delete the doc, rerun, byte-identical (modulo run times).
Usage: /usr/bin/python3 scripts/results_all.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from bneck2 import lab as LAB
    rows = LAB.load_receipts()
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r.get("hyp", "?"), []).append(r)
    sup = LAB.support_rate()
    lines = ["# Results ledger — all experiments (rebuilt from receipts)",
             "",
             f"runs={len(rows)} hypotheses={len(by)} "
             f"support={sup['rate']} 95% CI [{sup['lo']}, {sup['hi']}]",
             ""]
    for hyp in sorted(by):
        last = by[hyp][-1]
        flag = " (directional-only)" if last.get("directional_only") else ""
        res = last.get("result", {})
        note = str(res.get("note", ""))[:220]
        lines.append(f"## {hyp}: {last.get('verdict')}{flag} "
                     f"(n={last.get('n')}, runs={len(by[hyp])})")
        if note:
            lines.append(f"{note}")
        # key numbers
        keys = {k: v for k, v in res.items()
                if k in ("rho", "rho_penalized", "hit_rate", "mean_excess",
                         "composite_sharpe", "momentum_sharpe", "buyhold_sharpe",
                         "mean_excess_vs_universe", "support", "hits", "total",
                         "heavy_mean", "light_mean", "peak", "basket_mean", "spy")}
        if keys:
            lines.append("`" + json.dumps(keys) + "`")
        lines.append("")
    # live counters
    cov = LAB.verdict_coverage()
    lines.append(f"coverage: {cov['cells_tested']} cells tested, "
                 f"{cov['cells_triggered']} triggered ({cov['rows']} rows)")
    lines.append(f"triggered: {', '.join(cov.get('triggered_cells', []))}")
    out = ROOT / "docs" / "RESULTS-ALL.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(by)} hypotheses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
