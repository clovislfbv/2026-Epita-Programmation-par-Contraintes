"""Genere le front de Pareto risk-return pour plusieurs solveurs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.benchmark import pareto_front
from src.data import stats_from_returns, synthetic_returns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pareto front Sparse Markowitz")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=15.0)
    parser.add_argument("--output", type=str, default="results")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--n-points", type=int, default=8)
    parser.add_argument("--solvers", nargs="+", default=["GreedySharpe", "GA", "MILP-SCIP"])
    args = parser.parse_args(argv)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    returns, _ = synthetic_returns(n_assets=args.n, n_days=756, seed=args.seed)
    mu, cov = stats_from_returns(returns)
    lambdas = np.logspace(-1, 2, args.n_points)

    frames = []
    for s in args.solvers:
        df = pareto_front(mu, cov, K=args.k, lambdas=lambdas, solver=s, time_limit=args.time_limit)
        if not df.empty:
            frames.append(df)
    pareto = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    csv_path = out / "pareto.csv"
    pareto.to_csv(csv_path, index=False)
    print(f"pareto -> {csv_path}")

    fig, ax = plt.subplots(figsize=(8, 5))
    for s in args.solvers:
        sub = pareto[pareto["solver"] == s]
        if not sub.empty:
            ax.plot(sub["vol"], sub["ret"], "o-", label=s)
    ax.set_xlabel("Volatilite annualisee")
    ax.set_ylabel("Rendement annualise")
    ax.set_title(f"Front de Pareto (N={args.n}, K={args.k})")
    ax.grid(alpha=0.3)
    ax.legend()
    fig_path = out / "pareto.png"
    fig.tight_layout()
    fig.savefig(fig_path, dpi=130)
    plt.close(fig)
    print(f"figure pareto -> {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
