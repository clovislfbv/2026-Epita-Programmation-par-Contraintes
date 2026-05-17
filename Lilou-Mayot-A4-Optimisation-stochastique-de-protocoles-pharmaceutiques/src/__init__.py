"""
pharma_optim
============
Librairie d'optimisation stochastique de protocoles de chimiothérapie.

Modules
-------
models
    Structures de données : PKParameters, Patient, TreatmentWindow, OptResult.
pharmacokinetics
    Modèle PK à un compartiment, superposition linéaire multi-doses,
    métriques d'efficacité et de toxicité.
patients
    Génération de cohortes synthétiques et de scénarios de variabilité.
optimizers
    Trois stratégies d'optimisation : déterministe (CP-SAT), stochastique
    (SAA) et robuste (minimax).
visualization
    Tracés des profils PK, front de Pareto, violins et cartes de risque.
"""

from .models import PKParameters, Patient, TreatmentWindow, OptResult, DRUGS
from .pharmacokinetics import pk_iv, pk_multi, calc_efficacy, calc_toxicity
from .patients import generate_patients, generate_scenarios
from .optimizers import solve_deterministic, solve_stochastic, solve_robust, eval_scenarios

__all__ = [
    "PKParameters", "Patient", "TreatmentWindow", "OptResult", "DRUGS",
    "pk_iv", "pk_multi", "calc_efficacy", "calc_toxicity",
    "generate_patients", "generate_scenarios",
    "solve_deterministic", "solve_stochastic", "solve_robust", "eval_scenarios",
]


