"""bneck2 implied — market-implied scenario probabilities, stdlib port of the
vendored postagi_kernel/market_implied.py (which needs numpy/scipy).

Same problem: priced_impacts ~= X @ p, ridge toward a prior, box [0,1].
Solver here is projected gradient descent on the normal equations —
deterministic, fixed iterations, no dependencies. Returns solution +
residual + conditioning note. For audit-grade conditioning (SVD), use the
vendored kernel where numpy exists.
"""
from __future__ import annotations


def _matvec(a: list[list[float]], x: list[float]) -> list[float]:
    return [sum(r[j] * x[j] for j in range(len(x))) for r in a]


def _gram(x: list[list[float]]) -> list[list[float]]:
    n = len(x[0])
    g = [[0.0] * n for _ in range(n)]
    for row in x:
        for i in range(n):
            for j in range(n):
                g[i][j] += row[i] * row[j]
    return g


def infer_market_probabilities(x: list[list[float]], y: list[float],
                               ridge: float = 1e-3,
                               prior: list[float] | None = None,
                               iters: int = 5000) -> dict:
    """min ||Xp-y||^2 + ridge*||p-prior||^2 s.t. 0<=p<=1."""
    if not x or any(len(r) != len(x[0]) for r in x) or len(y) != len(x):
        raise ValueError("shape mismatch")
    k = len(x[0])
    p0 = list(prior) if prior else [0.5] * k
    g = _gram(x)
    for i in range(k):
        g[i][i] += ridge
    xty = [sum(x[r][i] * y[r] for r in range(len(x))) for i in range(k)]
    b = [xty[i] + ridge * p0[i] for i in range(k)]
    # Lipschitz step from Gershgorin row sums (safe, deterministic).
    lips = max(sum(abs(v) for v in row) for row in g) or 1.0
    step = 1.0 / lips
    p = list(p0)
    for _ in range(iters):
        grad = [sum(g[i][j] * p[j] for j in range(k)) - b[i]
                for i in range(k)]
        p = [min(1.0, max(0.0, p[i] - step * grad[i])) for i in range(k)]
    pred = _matvec(x, p)
    resid = sum((pred[i] - y[i]) ** 2 for i in range(len(y))) ** 0.5
    # Ill-conditioning flag: tiny diagonal after centering ~= collinear X.
    diags = [g[i][i] for i in range(k)]
    ill = min(diags) < 1e-9 * (max(diags) or 1.0)
    return {"p": [round(v, 4) for v in p],
            "residual": round(resid, 6), "iters": iters,
            "ill_conditioned": ill,
            "note": "SVD conditioning needs numpy; see imported/postagi_kernel"}
