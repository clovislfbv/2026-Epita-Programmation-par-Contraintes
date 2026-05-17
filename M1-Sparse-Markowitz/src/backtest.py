import numpy as np
import pandas as pd
from .data import stats_from_returns
from .milp_model import sparse_markowitz_milp
from .heuristics import greedy_sharpe, genetic_algorithm
from .cpsat_model import sparse_markowitz_cpsat


SOLVERS = {
    "CP-SAT": sparse_markowitz_cpsat,
    "MILP-SCIP": sparse_markowitz_milp,
    "GreedySharpe": greedy_sharpe,
    "GA": genetic_algorithm,
}


def rolling_backtest(returns, K, solvers=("GreedySharpe",), lam=5.0,
                     train_days=252, rebalance_days=21, w_max=0.30, w_min=0.01,
                     commission_bps=10.0, time_limit=20.0):
    T, n = returns.shape
    dates = returns.index
    history = {s: [] for s in solvers}
    weights_log = {s: [] for s in solvers}

    start = train_days
    step = rebalance_days
    prev_w = {s: np.zeros(n) for s in solvers}

    t = start
    while t < T:
        train = returns.iloc[t - train_days:t]
        mu, cov = stats_from_returns(train)
        future = returns.iloc[t:min(t + step, T)]
        for s in solvers:
            fn = SOLVERS[s]
            kwargs = dict(mu=mu, cov=cov, K=K, w_max=w_max, w_min=w_min, lam=lam)
            if s in ("CP-SAT", "MILP-SCIP"):
                kwargs["time_limit"] = time_limit
            try:
                res = fn(**kwargs)
                w = res["w"] if res["w"] is not None else prev_w[s]
            except Exception:
                w = prev_w[s]
            turnover = float(np.abs(w - prev_w[s]).sum())
            cost = turnover * (commission_bps / 10000.0)
            port_daily = future.to_numpy() @ w
            if len(port_daily) > 0:
                port_daily[0] -= cost
            for d, r in zip(future.index, port_daily):
                history[s].append({"date": d, "return": float(r)})
            weights_log[s].append({"date": dates[t], "w": w, "turnover": turnover})
            prev_w[s] = w
        t += step

    out = {}
    for s in solvers:
        df = pd.DataFrame(history[s]).set_index("date")
        df["cum"] = (1 + df["return"]).cumprod()
        mu_d = df["return"].mean()
        sd_d = df["return"].std()
        sharpe = (mu_d / sd_d * np.sqrt(252.0)) if sd_d > 0 else 0.0
        max_dd = ((df["cum"].cummax() - df["cum"]) / df["cum"].cummax()).max()
        out[s] = {
            "returns": df,
            "summary": {
                "ann_return": (1 + mu_d) ** 252 - 1,
                "ann_vol": sd_d * np.sqrt(252.0),
                "sharpe": sharpe,
                "max_drawdown": float(max_dd),
                "total_return": float(df["cum"].iloc[-1] - 1),
            },
            "weights": weights_log[s],
        }
    return out
