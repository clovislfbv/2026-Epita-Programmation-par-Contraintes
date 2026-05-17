import numpy as np
from ortools.sat.python import cp_model


def _cholesky_upper(cov, eps=1e-6):
    n = cov.shape[0]
    c = cov + eps * np.eye(n)
    L = np.linalg.cholesky(c)
    return L.T


def _rational_lambda(lam, max_den=1000):
    from fractions import Fraction
    f = Fraction(lam).limit_denominator(max_den)
    return f.numerator, f.denominator


def sparse_markowitz_cpsat(mu, cov, K, w_max=0.30, w_min=0.01, lam=5.0,
                           scale=1000, precision=100, time_limit=60.0,
                           sectors=None, sector_cap=None,
                           w_prev=None, turnover_cap=None,
                           lex_symmetry=False, num_workers=8, verbose=False):
    """Sparse Markowitz via CP-SAT (integer poids, quad via Cholesky).

    lex_symmetry: si True, impose un ordre lexicographique sur les z apres tri
    stable des actifs par mu decroissant, soit Z[idx[i]] >= Z[idx[i+1]] pour
    tout i. Combine a sum(Z)=K, ceci selectionne exactement les K plus grands
    mu (variante restrictive, utile comme baseline experimentale pour mesurer
    la valeur du choix de selection au-dela du top-K Sharpe).
    """
    n = len(mu)
    U = _cholesky_upper(cov)
    U_int = np.rint(U * precision).astype(int)
    mu_int = np.rint(np.asarray(mu) * scale * 100).astype(int)

    model = cp_model.CpModel()
    w_max_int = int(round(w_max * scale))
    w_min_int = int(round(w_min * scale))

    W = [model.NewIntVar(0, w_max_int, f"w_{i}") for i in range(n)]
    Z = [model.NewBoolVar(f"z_{i}") for i in range(n)]

    model.Add(sum(W) == scale)
    model.Add(sum(Z) == K)

    for i in range(n):
        model.Add(W[i] <= w_max_int * Z[i])
        model.Add(W[i] >= w_min_int * Z[i])

    if sectors is not None and sector_cap is not None:
        cap_int = int(round(sector_cap * scale))
        sectors = np.asarray(sectors)
        for s in np.unique(sectors):
            idx = np.where(sectors == s)[0]
            model.Add(sum(W[i] for i in idx) <= cap_int)

    if w_prev is not None and turnover_cap is not None:
        w_prev_int = np.rint(np.asarray(w_prev) * scale).astype(int)
        turn_int = int(round(turnover_cap * scale))
        abs_diffs = []
        for i in range(n):
            d = model.NewIntVar(0, 2 * scale, f"d_{i}")
            model.AddAbsEquality(d, W[i] - int(w_prev_int[i]))
            abs_diffs.append(d)
        model.Add(sum(abs_diffs) <= 2 * turn_int)

    if lex_symmetry:
        idx = np.argsort(-np.asarray(mu), kind="stable")
        for i in range(n - 1):
            model.Add(Z[int(idx[i])] >= Z[int(idx[i + 1])])

    y_bound = int(np.sum(np.abs(U_int)) * w_max_int + 1)
    risk_terms = []
    for k in range(n):
        expr = sum(int(U_int[k, i]) * W[i] for i in range(n))
        y_k = model.NewIntVar(-y_bound, y_bound, f"y_{k}")
        model.Add(y_k == expr)
        y_sq = model.NewIntVar(0, y_bound * y_bound, f"ysq_{k}")
        model.AddMultiplicationEquality(y_sq, [y_k, y_k])
        risk_terms.append(y_sq)

    total_risk = sum(risk_terms)
    total_ret = sum(int(mu_int[i]) * W[i] for i in range(n))
    # total_risk a un facteur d'echelle scale^2 * precision^2, total_ret un
    # facteur scale^2 * 100; g = precision^2 / 100 aligne les deux pour que
    # l'argmin du programme entier coincide avec celui de lam*w'Cov w - mu'w.
    risk_scale_factor = (scale ** 2) * (precision ** 2)
    ret_scale_factor = (scale ** 2) * 100
    g = max(1, int(risk_scale_factor // ret_scale_factor))
    lam_num, lam_den = _rational_lambda(lam)
    model.Minimize(lam_num * total_risk - lam_den * g * total_ret)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = num_workers
    solver.parameters.log_search_progress = verbose
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "w": None, "z": None, "objective": None,
                "ret": None, "risk": None, "runtime": solver.WallTime(), "solver": "CP-SAT"}

    w_sol = np.array([solver.Value(W[i]) / scale for i in range(n)])
    z_sol = np.array([solver.Value(Z[i]) for i in range(n)], dtype=int)
    ret = float(np.asarray(mu) @ w_sol)
    risk = float(w_sol @ cov @ w_sol)
    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "w": w_sol, "z": z_sol, "objective": solver.ObjectiveValue(),
        "ret": ret, "risk": risk, "runtime": solver.WallTime(),
        "solver": "CP-SAT",
    }
