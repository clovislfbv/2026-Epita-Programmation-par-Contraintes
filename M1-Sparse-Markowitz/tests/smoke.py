"""Demo rapide des 4 solveurs (N=30, K=8).

Pour la suite de validation, utiliser `pytest tests` (cf. tests/test_solvers.py).
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cpsat_model import sparse_markowitz_cpsat
from src.data import stats_from_returns, synthetic_returns
from src.heuristics import genetic_algorithm, greedy_sharpe
from src.milp_model import sparse_markowitz_milp


def _row(name, res):
    return (f"{name:10s} status={res['status']:10s} "
            f"ret={res['ret']:.4f} risk={res['risk']:.4f} "
            f"t={res['runtime']:.2f}s |z|={int(sum(res['z']))}")


def main() -> int:
    returns, _ = synthetic_returns(n_assets=30, n_days=504, seed=1)
    mu, cov = stats_from_returns(returns)
    K = 8

    t0 = time.perf_counter()
    runs = [
        ("MILP-SCIP", sparse_markowitz_milp(mu, cov, K=K, lam=5.0, time_limit=15.0)),
        ("CP-SAT", sparse_markowitz_cpsat(mu, cov, K=K, lam=5.0, time_limit=15.0)),
        ("Greedy", greedy_sharpe(mu, cov, K=K, lam=5.0)),
        ("GA", genetic_algorithm(mu, cov, K=K, lam=5.0, pop_size=40, n_gen=30, seed=1)),
    ]
    for name, res in runs:
        print(_row(name, res))
    print(f"\nTotal wall time: {time.perf_counter() - t0:.2f}s")
    print("Validation complete via: pytest tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
