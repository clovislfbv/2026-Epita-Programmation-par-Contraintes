import numpy as np
import time
import random
from deap import base, creator, tools


def _solve_qp_on_subset(mu, cov, idx, w_max=0.30, w_min=0.01, lam=5.0, ridge=1e-6):
    mu_s = mu[idx]
    C = cov[np.ix_(idx, idx)]
    k = len(idx)
    A = 2.0 * lam * C + ridge * np.eye(k)
    try:
        x = np.linalg.solve(A, mu_s)
    except np.linalg.LinAlgError:
        return None, None
    if x.sum() <= 0:
        x = np.ones(k) / k
    else:
        x = x / x.sum()
    x = np.clip(x, w_min, w_max)
    x = x / x.sum()
    for _ in range(50):
        over = x > w_max
        under = x < w_min
        if not over.any() and not under.any():
            break
        x = np.clip(x, w_min, w_max)
        x = x / x.sum()
    w_full = np.zeros(len(mu))
    w_full[idx] = x
    ret = float(mu @ w_full)
    risk = float(w_full @ cov @ w_full)
    return w_full, (ret, risk)


def greedy_sharpe(mu, cov, K, w_max=0.30, w_min=0.01, lam=5.0):
    t0 = time.perf_counter()
    n = len(mu)
    vols = np.sqrt(np.diag(cov))
    sharpe = mu / np.maximum(vols, 1e-8)
    picked = list(np.argsort(-sharpe)[:K])
    improved = True
    while improved:
        improved = False
        _, stats = _solve_qp_on_subset(mu, cov, picked, w_max, w_min, lam)
        if stats is None:
            break
        best_obj = lam * stats[1] - stats[0]
        best_swap = None
        for i in picked:
            for j in range(n):
                if j in picked:
                    continue
                trial = [x for x in picked if x != i] + [j]
                _, trial_stats = _solve_qp_on_subset(mu, cov, trial, w_max, w_min, lam)
                if trial_stats is None:
                    continue
                trial_obj = lam * trial_stats[1] - trial_stats[0]
                if trial_obj < best_obj - 1e-8:
                    best_obj = trial_obj
                    best_swap = (i, j)
        if best_swap is not None:
            old, new = best_swap
            picked.remove(old)
            picked.append(new)
            improved = True
    w, stats = _solve_qp_on_subset(mu, cov, picked, w_max, w_min, lam)
    ret, risk = stats
    z = np.zeros(len(mu), dtype=int)
    z[picked] = 1
    return {"status": "heuristic", "w": w, "z": z, "objective": lam * risk - ret,
            "ret": ret, "risk": risk, "runtime": time.perf_counter() - t0,
            "solver": "GreedySharpe"}


def genetic_algorithm(mu, cov, K, w_max=0.30, w_min=0.01, lam=5.0,
                      pop_size=80, n_gen=60, cxpb=0.7, mutpb=0.3, seed=0):
    t0 = time.perf_counter()
    n = len(mu)
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    if hasattr(creator, "FitnessMin"):
        del creator.FitnessMin
    if hasattr(creator, "Individual"):
        del creator.Individual
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)

    def init_ind():
        idx = list(np_rng.choice(n, size=K, replace=False))
        return creator.Individual(sorted(idx))

    def evaluate(ind):
        idx = list(set(ind))
        if len(idx) != K:
            return (1e9,)
        _, stats = _solve_qp_on_subset(mu, cov, idx, w_max, w_min, lam)
        if stats is None:
            return (1e9,)
        ret, risk = stats
        return (lam * risk - ret,)

    def crossover(a, b):
        common = list(set(a) & set(b))
        pool = list(set(a) | set(b))
        child1_rest = rng.sample([x for x in pool if x not in common], max(0, K - len(common)))
        child1 = common + child1_rest
        child1 = sorted(set(child1))[:K]
        while len(child1) < K:
            c = rng.randrange(n)
            if c not in child1:
                child1.append(c)
        common2 = list(set(a) & set(b))
        child2 = common2 + rng.sample([x for x in pool if x not in common2], max(0, K - len(common2)))
        child2 = sorted(set(child2))[:K]
        while len(child2) < K:
            c = rng.randrange(n)
            if c not in child2:
                child2.append(c)
        a[:] = sorted(child1)
        b[:] = sorted(child2)
        del a.fitness.values
        del b.fitness.values
        return a, b

    def mutate(ind):
        i = rng.randrange(K)
        candidates = [x for x in range(n) if x not in ind]
        if candidates:
            ind[i] = rng.choice(candidates)
            ind.sort()
        del ind.fitness.values
        return (ind,)

    toolbox = base.Toolbox()
    toolbox.register("individual", init_ind)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate)
    toolbox.register("mate", crossover)
    toolbox.register("mutate", mutate)
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=pop_size)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for _ in range(n_gen):
        offspring = toolbox.select(pop, len(pop))
        offspring = [creator.Individual(list(o)) for o in offspring]
        for a, b in zip(offspring[::2], offspring[1::2]):
            if rng.random() < cxpb:
                toolbox.mate(a, b)
        for ind in offspring:
            if rng.random() < mutpb:
                toolbox.mutate(ind)
        for ind in offspring:
            if not ind.fitness.valid:
                ind.fitness.values = toolbox.evaluate(ind)
        pop = tools.selBest(pop + offspring, pop_size)

    best = tools.selBest(pop, 1)[0]
    idx = list(set(best))
    w, stats = _solve_qp_on_subset(mu, cov, idx, w_max, w_min, lam)
    ret, risk = stats
    z = np.zeros(len(mu), dtype=int)
    z[idx] = 1
    return {"status": "heuristic", "w": w, "z": z, "objective": lam * risk - ret,
            "ret": ret, "risk": risk, "runtime": time.perf_counter() - t0,
            "solver": "GA"}
