"""Backtest OOS rolling sur 3 periodes + figure courbes cumulees."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.backtest import rolling_backtest
from src.data import split_periods, synthetic_returns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rolling backtest")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--time-limit", type=float, default=15.0)
    parser.add_argument("--output", type=str, default="results")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--n-days", type=int, default=1260)
    parser.add_argument("--solvers", nargs="+", default=["GreedySharpe", "GA"])
    parser.add_argument("--commission-bps", type=float, default=10.0)
    args = parser.parse_args(argv)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    returns, _ = synthetic_returns(n_assets=args.n, n_days=args.n_days, seed=args.seed)
    periods = split_periods(returns, n_periods=3, train_ratio=0.7)

    summary_rows = []
    cumulative_frames = []
    last_payloads = None
    for p_idx, (train, test) in enumerate(periods):
        full = pd.concat([train, test])
        bt = rolling_backtest(
            full,
            K=args.k,
            solvers=tuple(args.solvers),
            lam=5.0,
            train_days=126,
            rebalance_days=21,
            commission_bps=args.commission_bps,
            time_limit=args.time_limit,
        )
        for s, payload in bt.items():
            row = {"periode": p_idx + 1, "solver": s}
            row.update({k: round(v, 4) for k, v in payload["summary"].items()})
            summary_rows.append(row)
            df = payload["returns"].copy()
            df["periode"] = p_idx + 1
            df["solver"] = s
            cumulative_frames.append(df.reset_index())
        last_payloads = bt

    summary = pd.DataFrame(summary_rows)
    summary_path = out / "backtest.csv"
    summary.to_csv(summary_path, index=False)
    print(f"backtest summary -> {summary_path}")

    if cumulative_frames:
        cum = pd.concat(cumulative_frames, ignore_index=True)
        cum_path = out / "backtest_cum.csv"
        cum.to_csv(cum_path, index=False)
        print(f"backtest curves -> {cum_path}")

    if last_payloads is not None:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for s, payload in last_payloads.items():
            payload["returns"]["cum"].plot(ax=ax, label=s)
        ax.set_xlabel("Date")
        ax.set_ylabel("Valeur cumulee")
        ax.set_title("Backtest OOS - derniere periode")
        ax.grid(alpha=0.3)
        ax.legend()
        fig_path = out / "backtest.png"
        fig.tight_layout()
        fig.savefig(fig_path, dpi=130)
        plt.close(fig)
        print(f"figure backtest -> {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
