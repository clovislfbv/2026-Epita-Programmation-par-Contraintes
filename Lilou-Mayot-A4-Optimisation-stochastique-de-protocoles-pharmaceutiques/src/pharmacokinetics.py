"""
pharmacokinetics.py
===================
Modèle pharmacocinétique à un compartiment et métriques cliniques.

Fonctions
---------
pk_iv
    Concentration plasmatique après injection IV bolus (dose unique).
pk_multi
    Superposition linéaire pour un protocole multi-doses.
calc_efficacy
    Score d'efficacité : fraction du temps en zone thérapeutique.
calc_toxicity
    Score de toxicité : dépassement normalisé du seuil toxique effectif.

Notes
-----
Le modèle supposé est mono-compartimentaire avec élimination de premier ordre :

    C(t) = (Dose / Vd) · exp(−ke · t),    ke = ln(2) / t½

La **superposition linéaire** suppose que les administrations n'interagissent
pas sur la cinétique (ce qui est valide pour les médicaments dont la
pharmacocinétique est linéaire dans les gammes de dose considérées).

Références
----------
Agur, Z. et al. (1996). Cell Proliferation, 29(6), 359–374.
Fiandaca, G. et al. (2022). Cancers, 14(17), 4101.
"""

from __future__ import annotations

import numpy as np
from typing import List

from .models import PKParameters, Patient


# ─────────────────────────────────────────────────────────────────────────────
# Modèle PK
# ─────────────────────────────────────────────────────────────────────────────

def pk_iv(dose: float, pk: PKParameters, t: np.ndarray) -> np.ndarray:
    """
    Concentration plasmatique après injection IV bolus (dose unique).

    Modèle mono-compartimentaire :

    .. math::
        C(t) = \\frac{\\text{Dose}}{V_d} \\cdot e^{-k_e \\cdot t}

    Parameters
    ----------
    dose : float
        Dose administrée (mg).
    pk : PKParameters
        Paramètres PK du médicament.
    t : np.ndarray
        Temps écoulé depuis l'administration (h). Les valeurs négatives
        sont traitées comme 0 (pas de concentration avant l'injection).

    Returns
    -------
    np.ndarray
        Concentration plasmatique (mg/L), même forme que ``t``.
    """
    return (dose / pk.vd) * np.exp(-pk.ke * np.maximum(t, 0.0))


def pk_multi(
    doses: List[float],
    admin_hours: List[float],
    pk: PKParameters,
    t_eval: np.ndarray,
) -> np.ndarray:
    """
    Concentration plasmatique pour un protocole multi-doses (superposition).

    La concentration totale est la somme des contributions individuelles,
    ce qui est valide pour les médicaments à pharmacocinétique linéaire :

    .. math::
        C_{\\text{total}}(t) =
        \\sum_{i=1}^{N} \\frac{d_i}{V_d}
        \\cdot e^{-k_e (t - t_i)} \\cdot \\mathbb{1}[t \\geq t_i]

    Parameters
    ----------
    doses : list of float
        Doses administrées (mg), une valeur par administration.
    admin_hours : list of float
        Temps d'administration (h), même longueur que ``doses``.
    pk : PKParameters
        Paramètres PK du médicament (éventuellement ajustés au patient).
    t_eval : np.ndarray
        Grille temporelle d'évaluation (h).

    Returns
    -------
    np.ndarray
        Concentration totale (mg/L), même forme que ``t_eval``.
    """
    c = np.zeros_like(t_eval, dtype=float)
    for dose, t_adm in zip(doses, admin_hours):
        mask = t_eval >= t_adm
        c[mask] += pk_iv(dose, pk, t_eval[mask] - t_adm)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Métriques cliniques
# ─────────────────────────────────────────────────────────────────────────────

def calc_efficacy(
    c: np.ndarray,
    t: np.ndarray,
    pk: PKParameters,
    p_response: float = 0.7,
) -> float:
    """
    Score d'efficacité normalisé ∈ [0, 1].

    Mesure la fraction du temps passée au-dessus de la concentration minimale
    efficace, pondérée par la probabilité de réponse tumorale du patient :

    .. math::
        \\text{Eff} =
        p_{\\text{rép}} \\cdot
        \\frac{\\int_0^T \\mathbb{1}[C(t) \\geq C_{\\min,\\text{eff}}]\\,dt}{T}

    Parameters
    ----------
    c : np.ndarray
        Profil de concentration (mg/L).
    t : np.ndarray
        Grille temporelle (h), même forme que ``c``.
    pk : PKParameters
        Paramètres PK (seul ``cmin_eff`` est utilisé).
    p_response : float, optional
        Probabilité de réponse tumorale ∈ [0, 1]. Défaut : 0.7.

    Returns
    -------
    float
        Score d'efficacité ∈ [0, 1].
    """
    dt = np.diff(t)
    time_above = float(np.sum((c[:-1] >= pk.cmin_eff) * dt))
    T = float(t[-1] - t[0])
    return min(time_above / T * p_response, 1.0)


def calc_toxicity(
    c: np.ndarray,
    t: np.ndarray,
    pk: PKParameters,
    sensitivity: float = 1.0,
) -> float:
    """
    Score de toxicité normalisé ∈ [0, 1].

    Mesure le dépassement de la concentration maximale tolérable, normalisé
    par le seuil effectif du patient. Le seuil effectif tient compte de la
    sensibilité individuelle :

    .. math::
        C_{\\text{seuil}} = \\frac{C_{\\max,\\text{safe}}}{\\text{sens}}

    Un patient avec ``sensitivity > 1`` est plus fragile (seuil abaissé).
    La toxicité est alors :

    .. math::
        \\text{Tox} =
        \\frac{\\int_0^T \\max\\!\\left(C(t) - C_{\\text{seuil}},\\, 0\\right)dt}
              {C_{\\text{seuil}} \\cdot T}

    La normalisation par :math:`C_{\\text{seuil}} \\cdot T` garantit que
    la métrique reste dans [0, 1] et est comparable entre patients de
    sensibilités différentes.

    Parameters
    ----------
    c : np.ndarray
        Profil de concentration (mg/L).
    t : np.ndarray
        Grille temporelle (h), même forme que ``c``.
    pk : PKParameters
        Paramètres PK (seul ``cmax_safe`` est utilisé comme valeur nominale).
    sensitivity : float, optional
        Facteur de sensibilité du patient (sans dimension, > 0). Défaut : 1.0.

    Returns
    -------
    float
        Score de toxicité ∈ [0, 1].
    """
    threshold = pk.cmax_safe / sensitivity
    excess = np.maximum(c - threshold, 0.0)
    ref = threshold * float(t[-1] - t[0])
    return float(min(np.trapezoid(excess, t) / ref, 1.0)) if ref > 0 else 0.0


