"""
patients.py
===========
Génération de cohortes synthétiques et de scénarios de variabilité patient.

Fonctions
---------
generate_patients
    Génère une cohorte de patients synthétiques indépendants.
generate_scenarios
    Génère des scénarios de perturbation autour d'un patient de base.

Notes
-----
La variabilité inter-individuelle est modélisée par des distributions
log-normales sur les facteurs PK (renal_factor, hepatic_factor, sensitivity),
ce qui est cohérent avec la littérature PK de population (Sheiner & Ludden,
1992). Le coefficient de variation (CV) obtenu est approximativement égal
au paramètre σ de la log-normale pour des petites valeurs de σ.

    CV ≈ σ   (pour σ < 0.5)

Les valeurs utilisées (σ ≈ 0.25–0.35) correspondent à un CV de 25–35 %,
représentatif de la variabilité observée en oncologie clinique.
"""

from __future__ import annotations

import numpy as np
from typing import List

from .models import Patient


def generate_patients(n: int = 20, seed: int = 42) -> List[Patient]:
    """
    Génère une cohorte de patients synthétiques indépendants.

    Les paramètres de variabilité sont tirés selon :

    - BSA        ~ Normal(1.73, 0.18),  clippé dans [1.2, 2.4] m²
    - âge        ~ Normal(55, 12),      clippé dans [25, 80] ans
    - renal      ~ LogNormal(0, 0.30)   (CV ≈ 30 %)
    - hepatic    ~ LogNormal(0, 0.25)   (CV ≈ 25 %)
    - sensitivity~ LogNormal(0, 0.35)   (CV ≈ 35 %)
    - p_response ~ Beta(3, 1.5),        clippé dans [0.10, 0.98]

    Parameters
    ----------
    n : int, optional
        Nombre de patients à générer. Défaut : 20.
    seed : int, optional
        Graine du générateur aléatoire (reproductibilité). Défaut : 42.

    Returns
    -------
    list of Patient
        Cohorte de ``n`` patients synthétiques.
    """
    rng = np.random.default_rng(seed)
    return [
        Patient(
            pid=f"P{i+1:02d}",
            bsa=float(np.clip(rng.normal(1.73, 0.18), 1.2, 2.4)),
            age=int(np.clip(rng.normal(55, 12), 25, 80)),
            renal_factor=float(rng.lognormal(0, 0.30)),
            hepatic_factor=float(rng.lognormal(0, 0.25)),
            sensitivity=float(rng.lognormal(0, 0.35)),
            p_response=float(np.clip(rng.beta(3, 1.5), 0.10, 0.98)),
        )
        for i in range(n)
    ]


def generate_scenarios(
    base: Patient,
    n: int = 40,
    seed: int = 0,
) -> List[Patient]:
    """
    Génère des scénarios de variabilité autour d'un patient de base.

    Chaque scénario est une perturbation multiplicative (log-normale) des
    facteurs PK du patient de base, avec un CV réduit par rapport à
    :func:`generate_patients` pour rester dans un voisinage réaliste :

    - BSA         ~ Normal(base.bsa, 12 % de base.bsa), clippé dans [1.2, 2.4]
    - renal       ~ base.renal × LogNormal(0, 0.22)
    - hepatic     ~ base.hepatic × LogNormal(0, 0.18)
    - sensitivity ~ base.sensitivity × LogNormal(0, 0.28)
    - p_response  ~ base.p_response + Normal(0, 0.09), clippé dans [0.05, 0.98]

    Parameters
    ----------
    base : Patient
        Patient de référence autour duquel les scénarios sont centrés.
    n : int, optional
        Nombre de scénarios à générer. Défaut : 40.
    seed : int, optional
        Graine du générateur aléatoire. Défaut : 0.

    Returns
    -------
    list of Patient
        ``n`` variantes du patient de base.
    """
    rng = np.random.default_rng(seed)
    return [
        Patient(
            pid=f"{base.pid}_s{s:02d}",
            bsa=float(np.clip(rng.normal(base.bsa, 0.12 * base.bsa), 1.2, 2.4)),
            age=base.age,
            renal_factor=float(base.renal_factor * rng.lognormal(0, 0.22)),
            hepatic_factor=float(base.hepatic_factor * rng.lognormal(0, 0.18)),
            sensitivity=float(base.sensitivity * rng.lognormal(0, 0.28)),
            p_response=float(
                np.clip(base.p_response + rng.normal(0, 0.09), 0.05, 0.98)
            ),
        )
        for s in range(n)
    ]


