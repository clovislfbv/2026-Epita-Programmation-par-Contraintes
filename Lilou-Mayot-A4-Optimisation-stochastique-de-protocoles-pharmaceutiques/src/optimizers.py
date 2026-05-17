"""
optimizers.py
=============
Trois stratégies d'optimisation de protocoles de chimiothérapie.

Fonctions publiques
-------------------
eval_scenarios
    Évalue un protocole sur un ensemble de scénarios patients.
solve_deterministic
    Optimisation déterministe par CP-SAT (Google OR-Tools).
solve_stochastic
    Optimisation stochastique par Sample Average Approximation (SAA).
solve_robust
    Optimisation robuste minimax sur scénarios adverses.

Fonctions internes
------------------
_gen_candidates
    Génère des protocoles candidats valides par tirage aléatoire.

Notes
-----
**Approche déterministe (CP-SAT)**

    Le problème est formulé comme un problème de scheduling à variables
    entières et booléennes, résolu exactement par OR-Tools CP-SAT :

        max  proxy_eff(doses, jours) − λ · proxy_tox(doses)
        s.c. Σ doses ≤ cum_dose_max
             day_{i+1} − day_i ≥ interval_min   (si les deux slots sont actifs)
             dose_i ∈ {niveaux_discrets}
             day_i ∈ {0, …, T}

    L'objectif est un proxy entier de l'objectif PK réel (scaling S=1000).
    Les métriques PK réelles sont recalculées après résolution.

**Approche stochastique (SAA)**

    Sample Average Approximation : on maximise l'espérance empirique de
    l'objectif sur S scénarios :

        max_π  (1/S) Σ_s f(π, ξ_s)

    Implémentée par évaluation exhaustive de K candidats.

**Approche robuste (minimax)**

    On maximise l'objectif dans le pire cas parmi un ensemble de scénarios
    adverses (haute sensibilité, faible réponse) :

        max_π  min_{s ∈ S_adv} f(π, ξ_s)

Références
----------
Bertsimas, D. et al. (2016). INFORMS Journal on Computing.
Shapiro, A. et al. (2009). Lectures on Stochastic Programming.
OR-Tools CP-SAT : https://developers.google.com/optimization/cp/cp_solver
"""

from __future__ import annotations

import time
import numpy as np
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from .models import PKParameters, Patient, TreatmentWindow, OptResult
from .pharmacokinetics import pk_multi, calc_efficacy, calc_toxicity


# ─────────────────────────────────────────────────────────────────────────────
# Évaluation multi-scénarios
# ─────────────────────────────────────────────────────────────────────────────

def eval_scenarios(
    doses: List[float],
    days: List[int],
    pk: PKParameters,
    scenarios: List[Patient],
    horizon_days: int = 28,
    lam: float = 2.0,
    n_points: int = 2000,
) -> Dict:
    """
    Évalue un protocole sur un ensemble de scénarios patients.

    Pour chaque scénario, les paramètres PK sont ajustés au profil du patient,
    la concentration est simulée, puis l'efficacité, la toxicité et l'objectif
    sont calculés.

    Parameters
    ----------
    doses : list of float
        Doses absolues (mg) du protocole à évaluer.
    days : list of int
        Jours d'administration correspondants.
    pk : PKParameters
        Paramètres PK nominaux du médicament.
    scenarios : list of Patient
        Ensemble de scénarios (patients) sur lesquels évaluer le protocole.
    horizon_days : int, optional
        Horizon temporel de simulation (jours). Défaut : 28.
    lam : float, optional
        Poids de la toxicité dans l'objectif. Défaut : 2.0.
    n_points : int, optional
        Nombre de points de la grille temporelle. Défaut : 2000.

    Returns
    -------
    dict
        Dictionnaire de statistiques avec les clés :

        - ``eff_mean``, ``eff_std`` : moyenne et écart-type de l'efficacité
        - ``tox_mean``, ``tox_std`` : moyenne et écart-type de la toxicité
        - ``obj_mean``, ``obj_std`` : moyenne et écart-type de l'objectif
        - ``obj_worst``             : pire cas de l'objectif (min sur scénarios)
        - ``obj_var95``             : VaR à 95 % (percentile 5 de l'objectif)
        - ``objs``, ``effs``, ``toxs`` : listes des valeurs individuelles
    """
    if not doses:
        zero = {k: 0.0 for k in
                ["eff_mean", "eff_std", "tox_mean", "tox_std",
                 "obj_mean", "obj_std", "obj_worst", "obj_var95"]}
        zero.update({"objs": [], "effs": [], "toxs": []})
        return zero

    t_eval = np.linspace(0, horizon_days * 24, n_points)
    hours  = [d * 24 for d in days]
    effs, toxs, objs = [], [], []

    for sc in scenarios:
        pk_s = sc.adjusted_pk(pk)
        c    = pk_multi(doses, hours, pk_s, t_eval)
        e    = calc_efficacy(c, t_eval, pk_s, sc.p_response)
        t    = calc_toxicity(c, t_eval, pk_s, sc.sensitivity)
        effs.append(e)
        toxs.append(t)
        objs.append(e - lam * t)

    return {
        "eff_mean":  float(np.mean(effs)),
        "eff_std":   float(np.std(effs)),
        "tox_mean":  float(np.mean(toxs)),
        "tox_std":   float(np.std(toxs)),
        "obj_mean":  float(np.mean(objs)),
        "obj_std":   float(np.std(objs)),
        "obj_worst": float(np.min(objs)),
        "obj_var95": float(np.percentile(objs, 5)),
        "objs": objs,
        "effs": effs,
        "toxs": toxs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Génération de candidats
# ─────────────────────────────────────────────────────────────────────────────

def _gen_candidates(
    patient: Patient,
    pk: PKParameters,
    window: TreatmentWindow,
    n: int = 250,
    seed: int = 0,
) -> List[Tuple[List[float], List[int]]]:
    """
    Génère ``n`` protocoles candidats valides par tirage aléatoire.

    Un candidat est un tuple ``(doses, days)`` respectant :

    - les niveaux de dose discrets de ``window``
    - l'intervalle minimum entre administrations
    - la contrainte de dose cumulée maximale

    Parameters
    ----------
    patient : Patient
        Patient de référence (utilisé pour la BSA et la dose cumulée max).
    pk : PKParameters
        Paramètres PK nominaux (pour calculer cum_dose_max ajusté).
    window : TreatmentWindow
        Fenêtre de traitement définissant les contraintes.
    n : int, optional
        Nombre de candidats à générer. Défaut : 250.
    seed : int, optional
        Graine du générateur aléatoire. Défaut : 0.

    Returns
    -------
    list of tuple
        Liste de ``n`` tuples ``(doses: list[float], days: list[int])``.
    """
    rng      = np.random.default_rng(seed)
    pk_adj   = patient.adjusted_pk(pk)
    valid    = [d for d in window.dose_levels_per_m2 if d > 0]
    cands: List[Tuple] = []

    while len(cands) < n:
        n_active = rng.integers(1, window.n_max_doses + 1)
        days: List[int] = []
        last = 0

        for j in range(n_active):
            lo = last + (window.interval_min_days if j > 0 else 0)
            hi = window.horizon_days - (n_active - j - 1) * window.interval_min_days
            if lo > hi:
                break
            days.append(int(rng.integers(lo, hi + 1)))
            last = days[-1]

        if len(days) < n_active:
            continue

        doses = [float(rng.choice(valid)) * patient.bsa for _ in days]

        if sum(doses) <= pk_adj.cum_dose_max:
            cands.append((doses, days))

    return cands


# ─────────────────────────────────────────────────────────────────────────────
# Optimisation déterministe — CP-SAT
# ─────────────────────────────────────────────────────────────────────────────

def solve_deterministic(
    pk: PKParameters,
    patient: Patient,
    window: TreatmentWindow,
    lam: float = 2.0,
    time_limit: float = 30.0,
) -> OptResult:
    """
    Optimisation déterministe du protocole par CP-SAT (Google OR-Tools).

    Formulation
    -----------
    Variables :

    - ``dose_idx[i]`` ∈ {0, …, |D|−1} : indice dans ``dose_levels_per_m2``
    - ``admin_day[i]`` ∈ {0, …, T}    : jour d'administration
    - ``active[i]``   ∈ {0, 1}        : indicateur de slot actif

    Contraintes :

    1. ``active[i] = 1 ↔ dose_idx[i] > 0``
    2. Ordre temporel : ``admin_day[i] ≤ admin_day[i+1]``
    3. Intervalle min : ``admin_day[i+1] − admin_day[i] ≥ Δ_min``
       (appliqué seulement si les deux slots sont actifs)
    4. Dose cumulée : ``Σ dose_abs[i] ≤ cum_dose_max``
    5. Symétrie : ``active[i] ≥ active[i+1]`` (slots inactifs en fin)

    Objectif proxy (entier, scaling S=1000) :

        max  Σ dose_abs[i]  −  λ · Σ excess[i]  +  espacement

    où ``excess[i] = max(dose_abs[i] − 0.8 · Cmax_safe · Vd, 0)`` est un
    proxy de la toxicité de pointe, et ``espacement`` favorise une
    distribution régulière des doses sur l'horizon.

    Les métriques PK réelles (efficacité, toxicité) sont recalculées après
    résolution sur le profil de concentration simulé.

    Parameters
    ----------
    pk : PKParameters
        Paramètres PK nominaux du médicament.
    patient : Patient
        Patient de référence (les paramètres PK sont ajustés via
        :meth:`Patient.adjusted_pk`).
    window : TreatmentWindow
        Contraintes de scheduling.
    lam : float, optional
        Poids de la toxicité dans l'objectif proxy. Défaut : 2.0.
    time_limit : float, optional
        Limite de temps allouée au solveur (secondes). Défaut : 30.0.

    Returns
    -------
    OptResult
        Protocole optimal avec statut, doses, jours et métriques PK.
    """
    pk_adj = patient.adjusted_pk(pk)
    w      = window
    S      = 1000  # facteur de scaling pour coefficients entiers
    N      = w.n_max_doses

    model = cp_model.CpModel()

    # ── Variables ────────────────────────────────────────────────
    dose_idx  = [model.new_int_var(0, len(w.dose_levels_per_m2) - 1, f"di_{i}")  for i in range(N)]
    admin_day = [model.new_int_var(0, w.horizon_days,                  f"day_{i}") for i in range(N)]
    active    = [model.new_bool_var(f"act_{i}")                                   for i in range(N)]

    # Doses absolues scalées
    levels_sc = [int(d * patient.bsa * S) for d in w.dose_levels_per_m2]
    dose_abs  = []
    for i in range(N):
        dv = model.new_int_var(0, max(levels_sc), f"dabs_{i}")
        model.add_element(dose_idx[i], levels_sc, dv)
        dose_abs.append(dv)

    # ── Contrainte 1 : lien active / dose_idx ────────────────────
    for i in range(N):
        model.add(dose_idx[i] > 0).only_enforce_if(active[i])
        model.add(dose_idx[i] == 0).only_enforce_if(active[i].negated())

    # ── Contrainte 2 : ordre temporel ────────────────────────────
    for i in range(N - 1):
        model.add(admin_day[i] <= admin_day[i + 1])

    # ── Contrainte 3 : intervalle minimum ────────────────────────
    for i in range(N - 1):
        both = model.new_bool_var(f"both_{i}")
        model.add_bool_and([active[i], active[i + 1]]).only_enforce_if(both)
        model.add_bool_or([active[i].negated(), active[i + 1].negated()]).only_enforce_if(both.negated())
        model.add(admin_day[i + 1] - admin_day[i] >= w.interval_min_days).only_enforce_if(both)

    # ── Contrainte 4 : dose cumulée maximale ─────────────────────
    model.add(sum(dose_abs) <= int(pk_adj.cum_dose_max * S))

    # ── Contrainte 5 : symétrie ───────────────────────────────────
    for i in range(N - 1):
        model.add(active[i] >= active[i + 1])

    # ── Objectif proxy ────────────────────────────────────────────
    # Proxy toxicité : excès au-delà de 80 % du seuil Cmax_safe · Vd
    threshold = int(pk_adj.cmax_safe * pk_adj.vd * S * 0.80)
    tox_terms = []
    for i in range(N):
        exc = model.new_int_var(0, max(levels_sc), f"exc_{i}")
        model.add_max_equality(exc, [dose_abs[i] - threshold, model.new_constant(0)])
        tox_terms.append(exc)

    # Bonus d'espacement : favorise les protocoles bien distribués sur l'horizon
    spacing = model.new_int_var(0, w.horizon_days * 20, "sp")
    model.add(spacing == (admin_day[N - 1] - admin_day[0]) * 10)

    model.maximize(sum(dose_abs) - int(lam) * sum(tox_terms) + spacing)

    # ── Résolution ────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = False

    t0   = time.time()
    code = solver.solve(model)
    ms   = (time.time() - t0) * 1000

    status_map = {
        cp_model.OPTIMAL:    "OPTIMAL",
        cp_model.FEASIBLE:   "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN:    "UNKNOWN",
    }
    status = status_map.get(code, "UNKNOWN")

    if code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return OptResult(status, [], [], 0.0, 0.0, 0.0, 0.0, "det", ms, patient.pid)

    # ── Extraction et évaluation PK réelle ────────────────────────
    sol_doses, sol_days = [], []
    for i in range(N):
        if solver.value(active[i]):
            sol_doses.append(w.dose_levels_per_m2[solver.value(dose_idx[i])] * patient.bsa)
            sol_days.append(solver.value(admin_day[i]))

    t_ev = np.linspace(0, w.horizon_days * 24, 3000)
    c    = pk_multi(sol_doses, [d * 24 for d in sol_days], pk_adj, t_ev)
    eff  = calc_efficacy(c, t_ev, pk_adj, patient.p_response)
    tox  = calc_toxicity(c, t_ev, pk_adj, patient.sensitivity)

    return OptResult(
        status=status,
        doses=sol_doses,
        times_days=sol_days,
        cum_dose=sum(sol_doses),
        eff=eff,
        tox=tox,
        obj=eff - lam * tox,
        model="det",
        ms=ms,
        pid=patient.pid,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Optimisation stochastique — SAA
# ─────────────────────────────────────────────────────────────────────────────

def solve_stochastic(
    pk: PKParameters,
    patient: Patient,
    window: TreatmentWindow,
    lam: float = 2.0,
    n_scenarios: int = 50,
    n_candidates: int = 250,
    seed: int = 42,
) -> OptResult:
    """
    Optimisation stochastique par Sample Average Approximation (SAA).

    Maximise l'espérance empirique de l'objectif sur ``n_scenarios`` scénarios
    de variabilité patient, en évaluant ``n_candidates`` protocoles candidats :

    .. math::
        \\max_{\\pi \\in \\Pi}\\; \\hat{f}_S(\\pi) =
        \\frac{1}{S} \\sum_{s=1}^{S} f(\\pi, \\xi_s)

    Les scénarios sont générés autour de ``patient`` par
    :func:`pharma_optim.patients.generate_scenarios`.

    Parameters
    ----------
    pk : PKParameters
        Paramètres PK nominaux du médicament.
    patient : Patient
        Patient de référence.
    window : TreatmentWindow
        Contraintes de scheduling.
    lam : float, optional
        Poids de la toxicité. Défaut : 2.0.
    n_scenarios : int, optional
        Nombre de scénarios SAA. Défaut : 50.
    n_candidates : int, optional
        Nombre de protocoles candidats explorés. Défaut : 250.
    seed : int, optional
        Graine aléatoire. Défaut : 42.

    Returns
    -------
    OptResult
        Meilleur protocole trouvé (maximisant E[f]). L'attribut ``obj``
        contient la valeur de E[f] sur les scénarios SAA.
    """
    from .patients import generate_scenarios

    scenarios = generate_scenarios(patient, n_scenarios, seed)
    candidates = _gen_candidates(patient, pk, window, n_candidates, seed)

    t0 = time.time()
    best_mean, best_doses, best_days = -np.inf, [], []

    for doses, days in candidates:
        s = eval_scenarios(doses, days, pk, scenarios, window.horizon_days, lam)
        if s["obj_mean"] > best_mean:
            best_mean  = s["obj_mean"]
            best_doses = doses
            best_days  = days

    ms = (time.time() - t0) * 1000

    pk_adj = patient.adjusted_pk(pk)
    t_ev   = np.linspace(0, window.horizon_days * 24, 3000)
    c      = pk_multi(best_doses, [d * 24 for d in best_days], pk_adj, t_ev)

    return OptResult(
        status="FEASIBLE",
        doses=best_doses,
        times_days=best_days,
        cum_dose=sum(best_doses),
        eff=calc_efficacy(c, t_ev, pk_adj, patient.p_response),
        tox=calc_toxicity(c, t_ev, pk_adj, patient.sensitivity),
        obj=best_mean,
        model="sto",
        ms=ms,
        pid=patient.pid,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Optimisation robuste — minimax
# ─────────────────────────────────────────────────────────────────────────────

def solve_robust(
    pk: PKParameters,
    patient: Patient,
    window: TreatmentWindow,
    lam: float = 2.0,
    n_scenarios: int = 25,
    n_candidates: int = 250,
    seed: int = 42,
) -> OptResult:
    """
    Optimisation robuste minimax sur scénarios adverses.

    Maximise l'objectif dans le pire cas parmi un ensemble de scénarios
    adverses, sélectionnés pour leur haute sensibilité et faible réponse :

    .. math::
        \\max_{\\pi \\in \\Pi}\\; \\min_{s \\in \\mathcal{S}_{\\text{adv}}} f(\\pi, \\xi_s)

    Construction de :math:`\\mathcal{S}_{\\text{adv}}` : on génère
    ``2 × n_scenarios`` scénarios, puis on sélectionne la moitié avec le
    score d'adversité le plus élevé :

        adversité(s) = sensitivity_s − p_response_s

    Parameters
    ----------
    pk : PKParameters
        Paramètres PK nominaux du médicament.
    patient : Patient
        Patient de référence.
    window : TreatmentWindow
        Contraintes de scheduling.
    lam : float, optional
        Poids de la toxicité. Défaut : 2.0.
    n_scenarios : int, optional
        Nombre de scénarios adverses retenus. Défaut : 25.
    n_candidates : int, optional
        Nombre de protocoles candidats explorés. Défaut : 250.
    seed : int, optional
        Graine aléatoire. Défaut : 42.

    Returns
    -------
    OptResult
        Meilleur protocole trouvé (maximisant le pire cas). L'attribut
        ``obj`` contient la valeur du pire cas sur les scénarios adverses.
    """
    from .patients import generate_scenarios

    # Sélection des scénarios les plus adverses
    all_sc = generate_scenarios(patient, n_scenarios * 2, seed)
    all_sc.sort(key=lambda p: p.sensitivity - p.p_response, reverse=True)
    worst_sc   = all_sc[:n_scenarios]
    candidates = _gen_candidates(patient, pk, window, n_candidates, seed)

    t0 = time.time()
    best_wc, best_doses, best_days = -np.inf, [], []

    for doses, days in candidates:
        s = eval_scenarios(doses, days, pk, worst_sc, window.horizon_days, lam)
        if s["obj_worst"] > best_wc:
            best_wc    = s["obj_worst"]
            best_doses = doses
            best_days  = days

    ms = (time.time() - t0) * 1000

    pk_adj = patient.adjusted_pk(pk)
    t_ev   = np.linspace(0, window.horizon_days * 24, 3000)
    c      = pk_multi(best_doses, [d * 24 for d in best_days], pk_adj, t_ev)

    return OptResult(
        status="FEASIBLE",
        doses=best_doses,
        times_days=best_days,
        cum_dose=sum(best_doses),
        eff=calc_efficacy(c, t_ev, pk_adj, patient.p_response),
        tox=calc_toxicity(c, t_ev, pk_adj, patient.sensitivity),
        obj=best_wc,
        model="rob",
        ms=ms,
        pid=patient.pid,
    )


