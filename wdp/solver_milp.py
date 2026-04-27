"""Solveur PLNE (Programmation Linéaire en Nombres Entiers) pour le WDP.

Modélisation identique au solveur CP-SAT (mêmes variables, mêmes contraintes,
même objectif), mais résolue par PuLP avec le solver CBC (Coin-OR Branch and
Cut). Permet la comparaison de performances CP-SAT vs PLNE (livrable 4).

Variables :
    x[j] in {0, 1}  pour chaque offre j

Objectif :
    max  sum_j  price[j] * x[j]

Contraintes :
    (1) Exclusivité d'item   : sum_{j : i in S_j} x[j] <= 1
    (2) Budget global        : sum_j  price[j] * x[j] <= B
    (3) Budget par bidder    : sum_{j : bidder(j)=k} price[j]*x[j] <= B_k
    (4) XOR par groupe       : sum_{j in G} x[j] <= 1

Une fonction utilitaire ``solve_wdp_lp_relaxation`` est également exposée :
elle résout la **relaxation continue** (variables dans [0,1] au lieu de
{0,1}). La borne supérieure obtenue sert à mesurer le **gap d'intégralité**.
"""

from __future__ import annotations

import time
from typing import Optional

import pulp

from .instance import Allocation, Instance


def _build_model(
    instance: Instance,
    enforce_budget: bool,
    enforce_xor: bool,
    excluded_bidders: set[str],
    continuous: bool = False,
) -> tuple[pulp.LpProblem, dict[int, pulp.LpVariable]]:
    """Construit le modèle PuLP du WDP.

    Si ``continuous=True``, les variables sont dans [0,1] (relaxation linéaire).
    Sinon, elles sont binaires.
    """
    cat = "Continuous" if continuous else "Binary"
    model = pulp.LpProblem(f"WDP_{instance.name}", pulp.LpMaximize)

    x: dict[int, pulp.LpVariable] = {}
    for b in instance.bids:
        if b.bidder in excluded_bidders:
            continue
        x[b.id] = pulp.LpVariable(f"x_{b.id}", lowBound=0, upBound=1, cat=cat)

    # Objectif
    model += pulp.lpSum(b.price * x[b.id] for b in instance.bids if b.id in x)

    # (1) Exclusivité par item
    for item in instance.items:
        terms = [x[b.id] for b in instance.bids if b.id in x and item in b.items]
        if len(terms) >= 2:
            model += pulp.lpSum(terms) <= 1, f"item_{item}"

    # (2)(3) Budget
    if enforce_budget and instance.budget.is_active():
        if instance.budget.global_cap is not None:
            model += (
                pulp.lpSum(b.price * x[b.id] for b in instance.bids if b.id in x)
                <= instance.budget.global_cap
            ), "budget_global"
        for bidder, cap in instance.budget.per_bidder.items():
            if bidder in excluded_bidders:
                continue
            terms = [
                b.price * x[b.id]
                for b in instance.bids
                if b.id in x and b.bidder == bidder
            ]
            if terms:
                model += pulp.lpSum(terms) <= cap, f"budget_{bidder}"

    # (4) XOR
    if enforce_xor:
        for k, group in enumerate(instance.xor_groups):
            terms = [x[bid] for bid in group if bid in x]
            if len(terms) >= 2:
                model += pulp.lpSum(terms) <= 1, f"xor_{k}"

    return model, x


def solve_wdp_milp(
    instance: Instance,
    enforce_budget: bool = True,
    enforce_xor: bool = True,
    time_limit_s: float = 60.0,
    excluded_bidders: Optional[set[str]] = None,
    log: bool = False,
) -> Allocation:
    """Résout le WDP en PLNE (variables binaires) avec CBC.

    Signature identique à ``solver_cpsat.solve_wdp_cpsat`` pour faciliter la
    comparaison directe des deux solveurs.
    """
    excluded = excluded_bidders or set()
    model, x = _build_model(
        instance,
        enforce_budget=enforce_budget,
        enforce_xor=enforce_xor,
        excluded_bidders=excluded,
        continuous=False,
    )

    solver = pulp.PULP_CBC_CMD(msg=int(log), timeLimit=time_limit_s)

    t0 = time.perf_counter()
    status = model.solve(solver)
    elapsed = time.perf_counter() - t0

    status_name = pulp.LpStatus[status]
    if status_name == "Optimal":
        winners = sorted(
            bid_id for bid_id, var in x.items() if var.value() is not None and var.value() > 0.5
        )
        revenue = float(pulp.value(model.objective))
    else:
        winners = []
        revenue = 0.0

    return Allocation(
        winning_bid_ids=winners,
        revenue=revenue,
        status=status_name.upper(),
        solve_time=elapsed,
        solver="PLNE-CBC",
    )


def solve_wdp_lp_relaxation(
    instance: Instance,
    enforce_budget: bool = True,
    enforce_xor: bool = True,
    time_limit_s: float = 60.0,
    excluded_bidders: Optional[set[str]] = None,
) -> Allocation:
    """Résout la relaxation linéaire (variables dans [0,1]).

    La valeur optimale obtenue est une **borne supérieure** sur le revenu
    optimal entier. Le gap d'intégralité se calcule comme :
        gap = (revenue_LP - revenue_ILP) / revenue_ILP
    Plus le gap est petit, plus la PLNE est rapide à résoudre.
    """
    excluded = excluded_bidders or set()
    model, x = _build_model(
        instance,
        enforce_budget=enforce_budget,
        enforce_xor=enforce_xor,
        excluded_bidders=excluded,
        continuous=True,
    )

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_s)

    t0 = time.perf_counter()
    status = model.solve(solver)
    elapsed = time.perf_counter() - t0

    status_name = pulp.LpStatus[status]
    if status_name == "Optimal":
        # En relaxation, les "gagnants" peuvent être fractionnaires ;
        # on rapporte les bids avec x_j > 1e-6 comme indicatifs.
        winners = sorted(
            bid_id for bid_id, var in x.items() if var.value() is not None and var.value() > 1e-6
        )
        revenue = float(pulp.value(model.objective))
    else:
        winners = []
        revenue = 0.0

    return Allocation(
        winning_bid_ids=winners,
        revenue=revenue,
        status=status_name.upper(),
        solve_time=elapsed,
        solver="LP-relaxation",
    )
