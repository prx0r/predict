"""bneck2 obsolescence — Song Ma technological-obsolescence, stdlib port of
the vendored postagi_kernel/methods/obsolescence.py (exact published
transformation; paper-scale citation corpus stays external).

  Base(f,t-w) = externally-owned patents cited by f up to t-w.
  Cit_tau     = external citations in year tau to that fixed base.
  Obs^w(f,t)  = -[ln Cit_t - ln Cit_{t-w}].

Larger = faster decay in usefulness of the firm's fixed knowledge base.
Citations by f itself are excluded (external-use decay, not self-citation).
"""
from __future__ import annotations

import math


def technological_obsolescence(citations_start: float,
                               citations_end: float,
                               epsilon: float = 1e-9) -> float:
    if citations_start < 0 or citations_end < 0:
        raise ValueError("citation counts must be non-negative")
    return -(math.log(max(citations_end, epsilon))
             - math.log(max(citations_start, epsilon)))


def construct_technology_base(firm: str, cutoff_year: int,
                              backward_citations: list[dict]) -> set[str]:
    """Fixed external base from citation links
    {citing_firm, citing_year, cited_patent, cited_owner}."""
    base: set[str] = set()
    for r in backward_citations:
        if r.get("citing_firm") != firm or int(r.get("citing_year", 0)) > cutoff_year:
            continue
        if r.get("cited_owner") == firm:
            continue
        base.add(str(r.get("cited_patent")))
    return base


def external_citations_to_base(firm: str, year: int, technology_base: set[str],
                               forward_citations: list[dict]) -> int:
    return sum(1 for r in forward_citations
               if int(r.get("citing_year", -1)) == year
               and str(r.get("cited_patent")) in technology_base
               and r.get("citing_firm") != firm)


def firm_obsolescence(firm: str, endpoint_year: int, horizon: int,
                      backward_citations: list[dict],
                      forward_citations: list[dict]) -> dict:
    start = endpoint_year - horizon
    base = construct_technology_base(firm, start, backward_citations)
    if not base:
        return {"firm": firm, "year": endpoint_year, "base_size": 0,
                "obsolescence": None}
    c0 = external_citations_to_base(firm, start, base, forward_citations)
    c1 = external_citations_to_base(firm, endpoint_year, base, forward_citations)
    return {"firm": firm, "year": endpoint_year, "base_size": len(base),
            "citations_start": c0, "citations_end": c1,
            "obsolescence": round(technological_obsolescence(c0, c1), 4)}
