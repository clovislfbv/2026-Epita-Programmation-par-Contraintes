"""Backtest S&P 500 (Kaggle) : train = historique sauf la derniere annee,
test = la derniere annee. K varie ; PnL test par solveur. Cardinalite
exacte (sum(z) == K).

Prerequis : cle API Kaggle (voir README, section "Donnees S&P 500 Kaggle").
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
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.cpsat_model import sparse_markowitz_cpsat
from src.data import load_sp500_kaggle, stats_from_returns
from src.heuristics import genetic_algorithm, greedy_sharpe
from src.milp_model import sparse_markowitz_milp

SOLVERS = {
    "CP-SAT": sparse_markowitz_cpsat,
    "MILP-SCIP": sparse_markowitz_milp,
    "GreedySharpe": greedy_sharpe,
    "GA": genetic_algorithm,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest S&P 500 Kaggle, sweep K")
    parser.add_argument("--solvers", nargs="+", default=["GreedySharpe", "GA", "MILP-SCIP", "CP-SAT"],
                        help="sous-ensemble de %s" % list(SOLVERS))
    parser.add_argument("--k-min", type=int, default=10)
    parser.add_argument("--k-max", type=int, default=110)
    parser.add_argument("--k-step", type=int, default=20)
    parser.add_argument("--max-assets", type=int, default=150,
                        help="univers = N actions les plus liquides ; 0 = toutes (~500, lent)")
    parser.add_argument("--test-days", type=int, default=365,
                        help="taille du test set (derniere annee de bourse)")
    parser.add_argument("--lam", type=float, default=5.0)
    parser.add_argument("--w-max", type=float, default=0.30)
    parser.add_argument("--w-min", type=float, default=0.01)
    parser.add_argument("--time-limit", type=float, default=60.0,
                        help="time limit des solveurs exacts (CP-SAT / MILP)")
    parser.add_argument("--output", type=str, default="results")
    args = parser.parse_args(argv)

    unknown = [s for s in args.solvers if s not in SOLVERS]
    if unknown:
        parser.error(f"solveurs inconnus {unknown} ; choisir parmi {list(SOLVERS)}")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    max_assets = args.max_assets if args.max_assets > 0 else None
    returns = load_sp500_kaggle(max_assets=max_assets)
    n_assets = returns.shape[1]
    test = returns.iloc[-args.test_days:]
    train = returns.iloc[:-args.test_days]
    print(f"univers={n_assets} actifs | train={len(train)}j "
          f"({train.index[0].date()} -> {train.index[-1].date()}) | "
          f"test={len(test)}j ({test.index[0].date()} -> {test.index[-1].date()})")
    mu, cov = stats_from_returns(train)

    ks = list(range(args.k_min, args.k_max + 1, args.k_step))
    ks = [k for k in ks if k < n_assets]
    if not ks:
        parser.error(f"aucun K < n_assets={n_assets} dans [{args.k_min}, {args.k_max}]")

    rows = []
    curves = []
    for K in ks:
        for s in args.solvers:
            fn = SOLVERS[s]
            kwargs = dict(mu=mu, cov=cov, K=K, w_max=args.w_max,
                          w_min=args.w_min, lam=args.lam)
            if s in ("CP-SAT", "MILP-SCIP"):
                kwargs["time_limit"] = args.time_limit
            try:
                res = fn(**kwargs)
            except Exception as e:  # noqa: BLE001 - on logge et on continue le sweep
                print(f"  K={K:3d} {s:12s} ERREUR {e}")
                continue
            if res["w"] is None:
                print(f"  K={K:3d} {s:12s} {res['status']} (pas de solution)")
                continue

            w = res["w"]
            port_daily = test.to_numpy() @ w  # buy-and-hold sur le test set
            cum = np.cumprod(1.0 + port_daily)
            pnl = float(cum[-1] - 1.0)
            sd = float(port_daily.std())
            sharpe = float(port_daily.mean() / sd * np.sqrt(252.0)) if sd > 0 else 0.0
            run_max = np.maximum.accumulate(cum)
            max_dd = float(((run_max - cum) / run_max).max())
            rows.append({
                "K": K, "solver": s, "pnl": round(pnl, 4),
                "ann_vol": round(sd * np.sqrt(252.0), 4),
                "sharpe": round(sharpe, 3), "max_drawdown": round(max_dd, 4),
                "n_active": int(res["z"].sum()), "status": res["status"],
                "runtime_s": round(res["runtime"], 2),
            })
            for d, c in zip(test.index, cum):
                curves.append({"date": d, "K": K, "solver": s,
                               "cum": float(c)})
            print(f"  K={K:3d} {s:12s} pnl={pnl:+.4f} sharpe={sharpe:+.3f} "
                  f"t={res['runtime']:.2f}s")

    if not rows:
        print("aucun resultat")
        return 1

    summary = pd.DataFrame(rows)
    summary_path = out / "sp500_pnl.csv"
    summary.to_csv(summary_path, index=False)
    print(f"resume PnL -> {summary_path}")

    curve_df = pd.DataFrame(curves)
    curve_path = out / "sp500_pnl_curves.csv"
    curve_df.to_csv(curve_path, index=False)
    print(f"courbes cumulees -> {curve_path}")

    # Figure 1 : PnL final du test en fonction de K, une courbe par solveur.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s in args.solvers:
        sub = summary[summary["solver"] == s].sort_values("K")
        if not sub.empty:
            ax.plot(sub["K"], sub["pnl"], marker="o", label=s)
    ax.axhline(0.0, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("K (nombre d'actifs)")
    ax.set_ylabel("PnL test (derniere annee)")
    ax.set_title(f"S&P 500 - PnL out-of-sample par solveur (N={n_assets})")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    pnl_fig = out / "sp500_pnl.png"
    fig.savefig(pnl_fig, dpi=130)
    plt.close(fig)
    print(f"figure PnL vs K -> {pnl_fig}")

    # Figure 2 : une courbe cumulee par K (grille de sous-graphes).
    ncols = min(3, len(ks))
    nrows = (len(ks) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 3.2 * nrows),
                             squeeze=False, sharex=True)
    for ax_idx, K in enumerate(ks):
        ax = axes[ax_idx // ncols][ax_idx % ncols]
        kc = curve_df[curve_df["K"] == K]
        for s in args.solvers:
            sc = kc[kc["solver"] == s]
            if not sc.empty:
                ax.plot(sc["date"], sc["cum"], label=s)
        ax.axhline(1.0, color="grey", lw=0.8, ls="--")
        ax.set_title(f"K = {K}")
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", labelrotation=45)
    for empty in range(len(ks), nrows * ncols):
        axes[empty // ncols][empty % ncols].axis("off")
    axes[0][0].legend(loc="upper left", fontsize=8)
    fig.suptitle("S&P 500 - valeur cumulee test (1 = capital initial)")
    fig.tight_layout()
    curves_fig = out / "sp500_pnl_curves.png"
    fig.savefig(curves_fig, dpi=130)
    plt.close(fig)
    print(f"figure courbes par K -> {curves_fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
