import numpy as np
import pytest

from src.cpsat_model import sparse_markowitz_cpsat
from src.data import stats_from_returns, synthetic_returns
from src.heuristics import genetic_algorithm, greedy_sharpe
from src.milp_model import sparse_markowitz_milp


def _instance(n=20, k=5, seed=0):
    returns, meta = synthetic_returns(n_assets=n, n_days=378, seed=seed)
    mu, cov = stats_from_returns(returns)
    return mu, cov, meta, n, k


def _all_solvers(mu, cov, k, **kw):
    return {
        "MILP-SCIP": sparse_markowitz_milp(mu, cov, K=k, lam=5.0, time_limit=10.0, **kw),
        "CP-SAT": sparse_markowitz_cpsat(mu, cov, K=k, lam=5.0, time_limit=20.0, **kw),
        "Greedy": greedy_sharpe(mu, cov, K=k, lam=5.0, **kw),
        "GA": genetic_algorithm(mu, cov, K=k, lam=5.0, pop_size=40, n_gen=30, seed=0, **kw),
    }


def test_cardinality_exact():
    mu, cov, _, n, k = _instance()
    res = _all_solvers(mu, cov, k)
    for name, r in res.items():
        assert r["z"] is not None, f"{name} infeasible"
        assert int(r["z"].sum()) == k, f"{name}: |z|={int(r['z'].sum())} != K={k}"


def test_weights_sum_to_one():
    mu, cov, _, n, k = _instance()
    res = _all_solvers(mu, cov, k)
    for name, r in res.items():
        assert r["w"] is not None
        assert r["w"].sum() == pytest.approx(1.0, abs=5e-3), f"{name}: sum(w)={r['w'].sum()}"


def test_lower_bound_buyin():
    mu, cov, _, n, k = _instance()
    w_min = 0.01
    res = _all_solvers(mu, cov, k)
    for name, r in res.items():
        w, z = r["w"], r["z"]
        active = z.astype(bool)
        if active.any():
            assert (w[active] >= w_min - 1e-3).all(), f"{name}: w_active min={w[active].min()}"


def test_upper_bound_cap():
    mu, cov, _, n, k = _instance()
    w_max = 0.30
    res = _all_solvers(mu, cov, k)
    for name, r in res.items():
        assert (r["w"] <= w_max + 1e-3).all(), f"{name}: max(w)={r['w'].max()}"


def test_inactive_weights_zero():
    mu, cov, _, n, k = _instance()
    res = _all_solvers(mu, cov, k)
    for name, r in res.items():
        w, z = r["w"], r["z"]
        inactive = z == 0
        if inactive.any():
            assert (w[inactive] < 1e-3).all(), f"{name}: residue on inactive"


def test_sector_cap_milp():
    mu, cov, meta, n, k = _instance()
    sectors = meta["sector"].to_numpy()
    cap = 0.25
    r = sparse_markowitz_milp(mu, cov, K=k, lam=5.0, time_limit=10.0,
                              sectors=sectors, sector_cap=cap)
    assert r["w"] is not None
    for s in np.unique(sectors):
        exposure = float(r["w"][sectors == s].sum())
        assert exposure <= cap + 1e-3, f"sector {s} exposure {exposure} > {cap}"


def test_turnover_cap_milp():
    mu, cov, _, n, k = _instance()
    w_prev = np.zeros(n)
    w_prev[:k] = 1.0 / k
    cap = 0.4
    r = sparse_markowitz_milp(mu, cov, K=k, lam=5.0, time_limit=10.0,
                              w_prev=w_prev, turnover_cap=cap)
    assert r["w"] is not None
    turnover = float(np.abs(r["w"] - w_prev).sum())
    assert turnover <= 2 * cap + 1e-3, f"turnover {turnover} > 2*{cap}"


def test_milp_objective_le_greedy():
    mu, cov, _, n, k = _instance(seed=2)
    r_milp = sparse_markowitz_milp(mu, cov, K=k, lam=5.0, time_limit=15.0)
    r_greedy = greedy_sharpe(mu, cov, K=k, lam=5.0)
    obj_milp = 5.0 * r_milp["risk"] - r_milp["ret"]
    obj_greedy = 5.0 * r_greedy["risk"] - r_greedy["ret"]
    assert obj_milp <= obj_greedy + 1e-6, f"MILP obj {obj_milp} > Greedy {obj_greedy}"


def test_cpsat_feasible_small():
    mu, cov, _, n, k = _instance(n=20, k=5, seed=3)
    r = sparse_markowitz_cpsat(mu, cov, K=k, lam=5.0, time_limit=15.0)
    assert r["status"] in ("optimal", "feasible")
    assert int(r["z"].sum()) == k


def test_ga_beats_random():
    rng = np.random.default_rng(0)
    mu, cov, _, n, k = _instance(seed=4)
    n_trials = 30
    best_random = np.inf
    for _ in range(n_trials):
        idx = rng.choice(n, size=k, replace=False)
        from src.heuristics import _solve_qp_on_subset

        _, stats = _solve_qp_on_subset(mu, cov, idx, lam=5.0)
        if stats is not None:
            obj = 5.0 * stats[1] - stats[0]
            best_random = min(best_random, obj)
    r_ga = genetic_algorithm(mu, cov, K=k, lam=5.0, pop_size=40, n_gen=30, seed=0)
    obj_ga = 5.0 * r_ga["risk"] - r_ga["ret"]
    assert obj_ga <= best_random + 1e-6, f"GA obj {obj_ga} > best random {best_random}"


def test_lex_symmetry_consistent():
    mu, cov, _, n, k = _instance(seed=5)
    r_milp = sparse_markowitz_milp(mu, cov, K=k, lam=5.0, time_limit=10.0, lex_symmetry=True)
    r_cps = sparse_markowitz_cpsat(mu, cov, K=k, lam=5.0, time_limit=15.0, lex_symmetry=True)
    top_k = set(np.argsort(-mu)[:k].tolist())
    assert r_milp["z"] is not None and r_cps["z"] is not None
    sel_milp = set(np.where(r_milp["z"] == 1)[0].tolist())
    sel_cps = set(np.where(r_cps["z"] == 1)[0].tolist())
    assert sel_milp == top_k, f"MILP lex selection {sel_milp} != top-K mu {top_k}"
    assert sel_cps == top_k, f"CP-SAT lex selection {sel_cps} != top-K mu {top_k}"
