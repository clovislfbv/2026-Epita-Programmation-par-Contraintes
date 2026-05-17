"""Benchmark scalabilite + tableau de reference N=50 K=10."""
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

from src.benchmark import run_benchmark
from src.cpsat_model import sparse_markowitz_cpsat
from src.data import stats_from_returns, synthetic_returns
from src.heuristics import genetic_algorithm, greedy_sharpe
from src.milp_model import sparse_markowitz_milp


REF_N = 50
REF_K = 10
REF_LAM = 5.0


def reference_table(seed: int, time_limit: float) -> pd.DataFrame:
    returns, _ = synthetic_returns(n_assets=REF_N, n_days=756, seed=seed)
    mu, cov = stats_from_returns(returns)
    rows = []
    solvers = [
        ("MILP-SCIP", lambda: sparse_markowitz_milp(mu, cov, K=REF_K, lam=REF_LAM, time_limit=time_limit)),
        ("CP-SAT", lambda: sparse_markowitz_cpsat(mu, cov, K=REF_K, lam=REF_LAM, time_limit=time_limit)),
        ("Greedy", lambda: greedy_sharpe(mu, cov, K=REF_K, lam=REF_LAM)),
        ("GA", lambda: genetic_algorithm(mu, cov, K=REF_K, lam=REF_LAM, pop_size=80, n_gen=60, seed=seed)),
    ]
    for name, fn in solvers:
        r = fn()
        rows.append({
            "solver": name,
            "status": r["status"],
            "ret": round(r["ret"], 4),
            "vol": round(float(np.sqrt(r["risk"])), 4),
            "sharpe": round(r["ret"] / float(np.sqrt(r["risk"])), 3) if r["risk"] > 0 else None,
            "obj": round(r["objective"], 4) if r["objective"] is not None else None,
            "runtime_s": round(r["runtime"], 2),
            "K_active": int(r["z"].sum()),
        })
    return pd.DataFrame(rows)


def scalability_figure(df: pd.DataFrame, path: Path) -> None:
    pivot = df.dropna(subset=["runtime"]).pivot(index="N", columns="solver", values="runtime")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    pivot.plot(kind="bar", ax=ax)
    ax.set_ylabel("Temps (s)")
    ax.set_xlabel("N (nombre d'actifs)")
    ax.set_title("Scalabilite : temps de resolution")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Sparse Markowitz")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=15.0,
                        help="time limit pour le benchmark de scalabilite")
    parser.add_argument("--ref-time-limit", type=float, default=30.0,
                        help="time limit pour la table de reference N=50 K=10")
    parser.add_argument("--output", type=str, default="results")
    parser.add_argument("--sizes", type=int, nargs="+", default=[50, 100, 200])
    parser.add_argument("--skip-cpsat-above", type=int, default=100)
    parser.add_argument("--skip-milp-above", type=int, default=300)
    args = parser.parse_args(argv)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    ref = reference_table(seed=args.seed, time_limit=args.ref_time_limit)
    ref_path = out / "reference_n50_k10.csv"
    ref.to_csv(ref_path, index=False)
    print(f"reference table -> {ref_path}")
    print(ref.to_string(index=False))

    bench = run_benchmark(
        sizes=tuple(args.sizes),
        ratio_K=0.10,
        lam=REF_LAM,
        time_limit=args.time_limit,
        skip_cpsat_above=args.skip_cpsat_above,
        skip_milp_above=args.skip_milp_above,
        seed=args.seed,
    )
    bench_path = out / "bench.csv"
    bench.to_csv(bench_path, index=False)
    print(f"scalability bench -> {bench_path}")

    fig_path = out / "scalability.png"
    scalability_figure(bench, fig_path)
    print(f"figure scalability -> {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
