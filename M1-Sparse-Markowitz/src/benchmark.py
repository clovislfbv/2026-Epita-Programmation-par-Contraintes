import numpy as np
import pandas as pd
from .data import synthetic_returns, stats_from_returns
from .cpsat_model import sparse_markowitz_cpsat
from .milp_model import sparse_markowitz_milp
from .heuristics import greedy_sharpe, genetic_algorithm


SOLVERS = {
    "CP-SAT": sparse_markowitz_cpsat,
    "MILP-SCIP": sparse_markowitz_milp,
    "Greedy": greedy_sharpe,
    "GA": genetic_algorithm,
}


def run_benchmark(sizes=(50, 100, 200, 500, 1000), ratio_K=0.10, lam=5.0,
                  w_max=0.30, w_min=0.01, time_limit=30.0,
                  skip_cpsat_above=100, skip_milp_above=300, seed=0):
    rows = []
    for n in sizes:
        K = max(5, int(ratio_K * n))
        returns, meta = synthetic_returns(n_assets=n, seed=seed)
        mu, cov = stats_from_returns(returns)
        print(f"N={n}, K={K}")
        for name, fn in SOLVERS.items():
            if name == "CP-SAT" and n > skip_cpsat_above:
                rows.append({"N": n, "K": K, "solver": name, "status": "skipped",
                             "ret": None, "risk": None, "obj": None, "runtime": None})
                continue
            if name == "MILP-SCIP" and n > skip_milp_above:
                rows.append({"N": n, "K": K, "solver": name, "status": "skipped",
                             "ret": None, "risk": None, "obj": None, "runtime": None})
                continue
            kwargs = dict(mu=mu, cov=cov, K=K, w_max=w_max, w_min=w_min, lam=lam)
            if name in ("CP-SAT", "MILP-SCIP"):
                kwargs["time_limit"] = time_limit
            try:
                res = fn(**kwargs)
            except Exception as e:
                rows.append({"N": n, "K": K, "solver": name, "status": f"error:{e}",
                             "ret": None, "risk": None, "obj": None, "runtime": None})
                continue
            rows.append({"N": n, "K": K, "solver": name, "status": res["status"],
                         "ret": res["ret"], "risk": res["risk"],
                         "obj": res["objective"], "runtime": res["runtime"]})
            print(f"  {name:12s}  status={res['status']:10s}  ret={res['ret']}  risk={res['risk']}  t={res['runtime']:.2f}s")
    return pd.DataFrame(rows)


def pareto_front(mu, cov, K, lambdas=None, solver="GreedySharpe",
                 w_max=0.30, w_min=0.01, time_limit=20.0):
    if lambdas is None:
        lambdas = np.logspace(-1, 2, 10)
    fn = {
        "CP-SAT": sparse_markowitz_cpsat,
        "MILP-SCIP": sparse_markowitz_milp,
        "GreedySharpe": greedy_sharpe,
        "GA": genetic_algorithm,
    }[solver]
    points = []
    for lam in lambdas:
        kwargs = dict(mu=mu, cov=cov, K=K, w_max=w_max, w_min=w_min, lam=float(lam))
        if solver in ("CP-SAT", "MILP-SCIP"):
            kwargs["time_limit"] = time_limit
        res = fn(**kwargs)
        if res["w"] is not None:
            points.append({"lambda": float(lam), "ret": res["ret"],
                           "risk": res["risk"], "vol": np.sqrt(res["risk"]),
                           "solver": solver, "runtime": res["runtime"]})
    return pd.DataFrame(points)
