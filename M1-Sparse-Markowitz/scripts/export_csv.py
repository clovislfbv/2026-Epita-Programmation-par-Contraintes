"""Exporte les trois CSV consolides depuis results/.

- scalability.csv      : N, K, solver, status, ret, risk, obj, runtime_s
- backtest_oos.csv     : periode, solver, ann_return, ann_vol, sharpe,
                         max_drawdown, total_return
- symmetry_breaking.csv: N, K, lam, variante, status, runtime_s, obj,
                         support, is_top_K_mu

Les valeurs absentes (CP-SAT skipped, etc.) sont serialisees en NA explicite.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import numpy as np
import pandas as pd

from src.cpsat_model import sparse_markowitz_cpsat
from src.data import stats_from_returns, synthetic_returns


SCALABILITY_COLS = ["N", "K", "solver", "status", "ret", "risk", "obj", "runtime_s"]
BACKTEST_COLS = ["periode", "solver", "ann_return", "ann_vol", "sharpe", "max_drawdown", "total_return"]
SYMMETRY_COLS = ["N", "K", "lam", "variante", "status", "runtime_s", "obj", "support", "is_top_K_mu"]


def export_scalability(src: Path, dst: Path) -> pd.DataFrame:
    df = pd.read_csv(src)
    df = df.rename(columns={"runtime": "runtime_s"})
    df = df[SCALABILITY_COLS]
    df.to_csv(dst, index=False, na_rep="NA")
    return df


def export_backtest(src: Path, dst: Path) -> pd.DataFrame:
    df = pd.read_csv(src)
    df = df[BACKTEST_COLS]
    df.to_csv(dst, index=False, na_rep="NA")
    return df


def export_symmetry(dst: Path, n: int, k: int, lam: float, seed: int, time_limit: float) -> pd.DataFrame:
    returns, _ = synthetic_returns(n_assets=n, n_days=756, seed=seed)
    mu, cov = stats_from_returns(returns)
    top_k = sorted(np.argsort(-mu)[:k].tolist())

    rows = []
    for label, lex in (("sans lex", False), ("avec lex", True)):
        r = sparse_markowitz_cpsat(mu, cov, K=k, lam=lam, time_limit=time_limit, lex_symmetry=lex)
        support = sorted(np.where(r["z"] == 1)[0].tolist()) if r["z"] is not None else None
        rows.append({
            "N": n,
            "K": k,
            "lam": lam,
            "variante": label,
            "status": r["status"],
            "runtime_s": round(r["runtime"], 3) if r["runtime"] is not None else None,
            "obj": round(r["objective"], 3) if r["objective"] is not None else None,
            "support": ";".join(str(x) for x in support) if support is not None else None,
            "is_top_K_mu": (support == top_k) if support is not None else None,
        })
    df = pd.DataFrame(rows, columns=SYMMETRY_COLS)
    df.to_csv(dst, index=False, na_rep="NA")
    return df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export consolide des CSV")
    parser.add_argument("--results", type=str, default="results", help="dossier source/destination")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--lam", type=float, default=5.0)
    parser.add_argument("--time-limit", type=float, default=10.0)
    args = parser.parse_args(argv)

    results = Path(args.results)
    results.mkdir(parents=True, exist_ok=True)

    sca = export_scalability(results / "bench.csv", results / "scalability.csv")
    print(f"scalability.csv ({len(sca)} lignes) -> {results / 'scalability.csv'}")

    bt = export_backtest(results / "backtest.csv", results / "backtest_oos.csv")
    print(f"backtest_oos.csv ({len(bt)} lignes) -> {results / 'backtest_oos.csv'}")

    sym = export_symmetry(results / "symmetry_breaking.csv",
                          n=args.n, k=args.k, lam=args.lam,
                          seed=args.seed, time_limit=args.time_limit)
    print(f"symmetry_breaking.csv ({len(sym)} lignes) -> {results / 'symmetry_breaking.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
