#!/usr/bin/env python3
"""bneck2 revealed — frontier-lab revealed preference brief.

LabSignal-ranked commitments + diversification reading + digger ladder +
substrate gap + executive-capital ledger. The lab-moat view.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bneck2 import ceo as C
from bneck2 import diggers as D
from bneck2 import labs as L
from bneck2 import patents as P


def main() -> int:
    deals = L.load_deals()
    commits = L.load_commitments()
    print(L.gap_report(deals))
    print("\n# Ranked capital commitments (LabSignal = log1p($) x irrev x spec x rel x dur)")
    for c in L.rank_commitments(commits)[:8]:
        flag = " (est $)" if c.get("estimated_amount") and c.get("amount_usd") else ""
        print(f"  {c['score']:8.2f} {c['lab']:9} {c['target'][:52]:52} [{c['kind']}]{flag}")
    print("\n" + L.diversification_reading(commits))
    print("\n" + D.board(D.load_diggers()))
    fto = P.load_map()
    ionq = P.legal_chokepoint(fto, "IonQ")
    print(f"\n# Patent FTO — IonQ tollbooth: {ionq['blocked']}/{ionq['architectures']} architectures blocked "
          f"(share {ionq['share']:.2f})")
    print("\n" + C.report(C.load_ledger()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
