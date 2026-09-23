"""bneck2 kernel_bridge — use vendored postagi_kernel when deps allow.

The kernel needs numpy/pandas/networkx/sklearn/scipy (absent on this
stdlib-only box). This bridge: (1) reports availability, (2) loads the
kernel's DEMO panel with csv (no deps), (3) delegates scoring to the kernel
only when importable, else points at the native worlds.py equivalent.

No silent substitution: every path declares itself.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "imported" / "postagi_kernel"
DEMO_COMPANIES = KERNEL / "data" / "demo_companies.csv"
DEMO_PANEL = KERNEL / "data" / "demo_backtest_panel.csv"


def deps_status() -> dict:
    out = {}
    for mod in ("numpy", "pandas", "networkx", "sklearn", "scipy", "yaml"):
        try:
            __import__(mod)
            out[mod] = True
        except ImportError:
            out[mod] = False
    return out


def kernel_available() -> bool:
    if not all(deps_status().get(m) for m in ("numpy", "pandas", "networkx")):
        return False
    sys.path.insert(0, str(KERNEL))
    try:
        import postagi_kernel  # noqa: F401
        return True
    except Exception:
        return False


def demo_companies() -> list[dict]:
    with open(DEMO_COMPANIES, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def demo_panel() -> list[dict]:
    with open(DEMO_PANEL, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def describe() -> dict:
    """What the kernel offers vs the native equivalent, honestly mapped."""
    return {
        "kernel_available": kernel_available(),
        "missing_deps": [m for m, ok in deps_status().items() if not ok],
        "native_equivalents": {
            "world_graph+obsolescence": "bneck2/worlds.py + bneck2/obsolescence.py (exact Ma, stdlib)",
            "market_implied": "bneck2/implied.py (stdlib ridge) + belief.py pm clock + calibration.py",
            "backtest panel": "bneck2/backtest.py (stdlib walk-forward) over imported demo CSVs",
            "techtoken/patentomics/convergence/mirai": "no native equivalent yet — papers only",
        },
    }
