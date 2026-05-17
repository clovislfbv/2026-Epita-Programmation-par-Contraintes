"""
models.py
=========
Structures de données partagées par tous les modules de la librairie.

Classes
-------
PKParameters
    Paramètres pharmacocinétiques d'un médicament (modèle mono-compartimentaire).
Patient
    Profil patient avec facteurs de variabilité inter-individuelle.
TreatmentWindow
    Fenêtre de traitement : horizon, niveaux de dose, contraintes de scheduling.
OptResult
    Résultat d'une optimisation (doses, jours, métriques).

Constantes
----------
DRUGS : dict[str, PKParameters]
    Catalogue de quatre médicaments chimiothérapeutiques de référence.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List


# ─────────────────────────────────────────────────────────────────────────────
# Paramètres pharmacocinétiques
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PKParameters:
    """
    Paramètres d'un médicament pour le modèle PK à un compartiment (IV bolus).

    Le modèle suppose une élimination de premier ordre :
    C(t) = (Dose / Vd) * exp(-ke * t), avec ke = ln(2) / t_half.

    Parameters
    ----------
    name : str
        Nom du médicament.
    ke : float
        Taux d'élimination (h⁻¹).
    vd : float
        Volume de distribution (L).
    t_half : float
        Demi-vie plasmatique (h).
    cmax_safe : float
        Concentration plasmatique maximale tolérée (mg/L).
        Au-delà de ce seuil la toxicité est comptabilisée.
    cmin_eff : float
        Concentration minimale efficace (mg/L).
        En dessous de ce seuil le médicament n'a pas d'effet thérapeutique.
    cum_dose_max : float
        Dose cumulée maximale admissible sur l'ensemble du cycle (mg).
        Reflète la toxicité cumulative (ex. cardiotoxicité de la doxorubicine).
    """

    name: str
    ke: float
    vd: float
    t_half: float
    cmax_safe: float
    cmin_eff: float
    cum_dose_max: float


# ─────────────────────────────────────────────────────────────────────────────
# Profil patient
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Patient:
    """
    Profil patient avec variabilité inter-individuelle.

    Les facteurs multiplicatifs (renal_factor, hepatic_factor, sensitivity)
    permettent d'ajuster les paramètres PK nominaux du médicament à un patient
    donné via la méthode :meth:`adjusted_pk`.

    Parameters
    ----------
    pid : str
        Identifiant unique du patient.
    bsa : float
        Surface corporelle (m²). Détermine la dose absolue à partir de la
        dose en mg/m².
    age : int
        Âge (années).
    renal_factor : float
        Facteur multiplicatif sur ke (> 1 → élimination accélérée).
    hepatic_factor : float
        Facteur multiplicatif sur Vd (> 1 → distribution élargie).
    sensitivity : float
        Facteur de sensibilité à la toxicité (> 1 → seuil Cmax_safe abaissé).
        Le seuil effectif est cmax_safe / sensitivity.
    p_response : float
        Probabilité de réponse tumorale ∈ [0, 1].
        Multiplie le score d'efficacité pour refléter l'hétérogénéité tumorale.
    """

    pid: str
    bsa: float
    age: int
    renal_factor: float
    hepatic_factor: float
    sensitivity: float
    p_response: float

    def adjusted_pk(self, base: PKParameters) -> PKParameters:
        """
        Retourne les paramètres PK ajustés pour ce patient.

        Les ajustements appliqués sont :

        - ke_adj = base.ke × renal_factor
        - vd_adj = base.vd × hepatic_factor × (bsa / 1.73)
        - t_half_adj = ln(2) / ke_adj
        - cmax_safe_adj = base.cmax_safe / sensitivity
        - cum_dose_max_adj = base.cum_dose_max × (bsa / 1.73)

        Parameters
        ----------
        base : PKParameters
            Paramètres nominaux du médicament (population de référence BSA=1.73).

        Returns
        -------
        PKParameters
            Paramètres ajustés pour ce patient.
        """
        ke_adj = base.ke * self.renal_factor
        vd_adj = base.vd * self.hepatic_factor * (self.bsa / 1.73)
        return PKParameters(
            name=base.name,
            ke=ke_adj,
            vd=vd_adj,
            t_half=np.log(2) / ke_adj,
            cmax_safe=base.cmax_safe / self.sensitivity,
            cmin_eff=base.cmin_eff,
            cum_dose_max=base.cum_dose_max * (self.bsa / 1.73),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre de traitement
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TreatmentWindow:
    """
    Paramètres de la fenêtre de traitement.

    Définit les contraintes de scheduling utilisées par tous les optimiseurs.

    Parameters
    ----------
    horizon_days : int
        Durée totale du cycle de traitement (jours). Défaut : 28.
    n_max_doses : int
        Nombre maximal d'administrations sur le cycle. Défaut : 6.
    interval_min_days : int
        Intervalle minimal obligatoire entre deux administrations consécutives
        (jours). Reflète le temps de récupération médullaire. Défaut : 3.
    dose_levels_per_m2 : list of float
        Niveaux de dose discrets autorisés (mg/m²). La valeur 0 indique
        l'absence d'administration. Défaut : [0, 25, 50, 75, 100].
    """

    horizon_days: int = 28
    n_max_doses: int = 6
    interval_min_days: int = 3
    dose_levels_per_m2: List[float] = field(
        default_factory=lambda: [0, 25, 50, 75, 100]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Résultat d'optimisation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OptResult:
    """
    Résultat d'une procédure d'optimisation.

    Parameters
    ----------
    status : str
        Statut du solveur : ``'OPTIMAL'``, ``'FEASIBLE'``, ``'INFEASIBLE'``,
        ``'UNKNOWN'``.
    doses : list of float
        Doses administrées (mg), une valeur par administration retenue.
    times_days : list of int
        Jours d'administration (entiers ∈ [0, horizon_days]).
    cum_dose : float
        Dose cumulée totale (mg).
    eff : float
        Score d'efficacité nominale ∈ [0, 1] (calculé sur le patient de base).
    tox : float
        Score de toxicité nominale ∈ [0, 1] (calculé sur le patient de base).
    obj : float
        Valeur de l'objectif nominal : eff - λ·tox, ou E[f] pour SAA,
        ou min f pour robuste.
    model : str
        Identifiant de la méthode : ``'det'``, ``'sto'``, ``'rob'``.
    ms : float
        Temps de résolution en millisecondes.
    pid : str
        Identifiant du patient de base (optionnel).
    """

    status: str
    doses: List[float]
    times_days: List[int]
    cum_dose: float
    eff: float
    tox: float
    obj: float
    model: str
    ms: float
    pid: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Catalogue de médicaments
# ─────────────────────────────────────────────────────────────────────────────

DRUGS: dict = {
    "doxorubicin": PKParameters(
        name="Doxorubicine",
        ke=np.log(2) / 30,   # t½ ≈ 30 h
        vd=809,
        t_half=30,
        cmax_safe=0.05,
        cmin_eff=0.005,
        cum_dose_max=550 * 1.73,  # 550 mg/m² × BSA_ref
    ),
    "fluorouracil": PKParameters(
        name="5-Fluorouracile",
        ke=np.log(2) / 0.17,  # t½ ≈ 10 min (IV bolus)
        vd=22,
        t_half=0.17,
        cmax_safe=0.8,
        cmin_eff=0.2,
        cum_dose_max=2400 * 1.73,
    ),
    "carboplatin": PKParameters(
        name="Carboplatine",
        ke=np.log(2) / 5.5,   # t½ ≈ 5.5 h
        vd=16,
        t_half=5.5,
        cmax_safe=8.0,
        cmin_eff=2.0,
        cum_dose_max=6000 * 1.73,
    ),
    "paclitaxel": PKParameters(
        name="Paclitaxel",
        ke=np.log(2) / 13,    # t½ ≈ 13 h
        vd=227,
        t_half=13,
        cmax_safe=0.1,
        cmin_eff=0.01,
        cum_dose_max=1750 * 1.73,
    ),
}
"""
dict[str, PKParameters] : Catalogue de quatre médicaments de référence.

Clés disponibles : ``'doxorubicin'``, ``'fluorouracil'``,
``'carboplatin'``, ``'paclitaxel'``.

Les paramètres sont issus de la littérature clinique (valeurs nominales
pour une population adulte de référence, BSA = 1.73 m²).
"""


