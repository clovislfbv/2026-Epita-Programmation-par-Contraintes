import numpy as np
from pyscipopt import Model, quicksum


def sparse_markowitz_milp(mu, cov, K, w_max=0.30, w_min=0.01, lam=5.0,
                          sectors=None, sector_cap=None,
                          w_prev=None, turnover_cap=None,
                          integer_lots=False, lot_size=100, budget=1_000_000,
                          prices=None,
                          lex_symmetry=False, time_limit=60.0, verbose=False):
    """Sparse Markowitz MIQP via SCIP.

    lex_symmetry: meme convention que la version CP-SAT, z[idx[i]] >= z[idx[i+1]]
    apres tri stable des actifs par mu decroissant. Cette variante restrictive
    force la selection des K plus grands mu et sert de baseline experimentale.
    """
    n = len(mu)
    mu = np.asarray(mu, dtype=float)
    cov = np.asarray(cov, dtype=float)

    m = Model("sparse_markowitz")
    m.setParam("limits/time", time_limit)
    if not verbose:
        m.hideOutput()

    w = [m.addVar(name=f"w_{i}", vtype="C", lb=0.0, ub=w_max) for i in range(n)]
    z = [m.addVar(name=f"z_{i}", vtype="B") for i in range(n)]

    m.addCons(quicksum(w) == 1.0)
    m.addCons(quicksum(z) == K)

    for i in range(n):
        m.addCons(w[i] <= w_max * z[i])
        m.addCons(w[i] >= w_min * z[i])

    if sectors is not None and sector_cap is not None:
        sectors = np.asarray(sectors)
        for s in np.unique(sectors):
            idx = np.where(sectors == s)[0]
            m.addCons(quicksum(w[i] for i in idx) <= sector_cap)

    if w_prev is not None and turnover_cap is not None:
        w_prev = np.asarray(w_prev)
        d_pos = [m.addVar(name=f"dp_{i}", vtype="C", lb=0.0) for i in range(n)]
        d_neg = [m.addVar(name=f"dn_{i}", vtype="C", lb=0.0) for i in range(n)]
        for i in range(n):
            m.addCons(w[i] - float(w_prev[i]) == d_pos[i] - d_neg[i])
        m.addCons(quicksum(d_pos[i] + d_neg[i] for i in range(n)) <= 2 * turnover_cap)

    if integer_lots and prices is not None:
        prices = np.asarray(prices)
        n_lots = [m.addVar(name=f"lots_{i}", vtype="I", lb=0) for i in range(n)]
        for i in range(n):
            m.addCons(w[i] * budget == n_lots[i] * lot_size * prices[i])

    if lex_symmetry:
        idx = np.argsort(-mu, kind="stable")
        for i in range(n - 1):
            m.addCons(z[int(idx[i])] >= z[int(idx[i + 1])])

    risk_expr = quicksum(cov[i, j] * w[i] * w[j] for i in range(n) for j in range(n))
    ret_expr = quicksum(mu[i] * w[i] for i in range(n))
    risk_var = m.addVar(name="risk", vtype="C", lb=0.0)
    ret_var = m.addVar(name="ret", vtype="C", lb=-1e6)
    m.addCons(risk_var >= risk_expr)
    m.addCons(ret_var == ret_expr)
    m.setObjective(lam * risk_var - ret_var, "minimize")

    m.optimize()
    status = m.getStatus()
    runtime = m.getSolvingTime()

    if status not in ("optimal", "timelimit", "gaplimit") or m.getNSols() == 0:
        return {"status": status, "w": None, "z": None, "objective": None,
                "ret": None, "risk": None, "runtime": runtime, "solver": "MILP-SCIP"}

    w_sol = np.array([m.getVal(w[i]) for i in range(n)])
    z_sol = np.array([int(round(m.getVal(z[i]))) for i in range(n)], dtype=int)
    w_sol = np.clip(w_sol, 0, None)
    s = w_sol.sum()
    if s > 0:
        w_sol = w_sol / s
    r_ret = float(mu @ w_sol)
    r_risk = float(w_sol @ cov @ w_sol)
    return {"status": "optimal" if status == "optimal" else status,
            "w": w_sol, "z": z_sol, "objective": m.getObjVal(),
            "ret": r_ret, "risk": r_risk, "runtime": runtime, "solver": "MILP-SCIP"}
