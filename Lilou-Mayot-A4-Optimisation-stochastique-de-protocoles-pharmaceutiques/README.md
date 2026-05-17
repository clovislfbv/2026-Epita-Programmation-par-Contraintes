# Groupe A4 — Optimisation Stochastique de Protocoles Pharmaceutiques

## Structure du projet

```
Lilou-Mayot-A4-Optimisation-stochastique-de-protocoles-pharmaceutiques/
├── src/
│   ├── __init__.py          # Exports publics du package
│   ├── models.py            # PKParameters, Patient, TreatmentWindow, OptResult, DRUGS
│   ├── pharmacokinetics.py  # pk_iv, pk_multi, calc_efficacy, calc_toxicity
│   ├── patients.py          # generate_patients, generate_scenarios
│   ├── optimizers.py        # solve_deterministic, solve_stochastic, solve_robust, eval_scenarios
│   └── visualization.py     # Fonctions de tracé
├── notebooks/
│   ├── A4_pharma_optimisation.ipynb  # Notebook d'analyse et de démonstration
│   └── figures/                      # Figures générées à l'exécution
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

Le notebook est le point d'entrée principal. Depuis le dossier `notebooks/` :

```bash
jupyter lab A4_pharma_optimisation.ipynb
```

La librairie `src/` peut aussi être utilisée directement :

```python
import sys
sys.path.insert(0, '..')   # depuis notebooks/, remonte à la racine

from src import DRUGS, generate_patients, TreatmentWindow
from src import solve_deterministic, solve_stochastic, solve_robust, eval_scenarios

pk      = DRUGS['doxorubicin']
patient = generate_patients(n=1, seed=42)[0]
window  = TreatmentWindow()

result = solve_deterministic(pk, patient, window, lam=2.0)
print(result.doses, result.times_days)
```

## Architecture

### Séparation des responsabilités

| Composant | Rôle |
|-----------|------|
| `src/models.py` | Structures de données partagées et catalogue de médicaments |
| `src/pharmacokinetics.py` | Modèle PK et métriques cliniques |
| `src/patients.py` | Génération de cohortes synthétiques et de scénarios |
| `src/optimizers.py` | Trois stratégies d'optimisation |
| `src/visualization.py` | Tracés des protocoles et analyses comparatives |
| `notebooks/A4_pharma_optimisation.ipynb` | Analyse, démonstration, figures |

### Modèle pharmacocinétique

Modèle à un compartiment (IV bolus) :

$$C(t) = \frac{\text{Dose}}{V_d} \cdot e^{-k_e t} \qquad k_e = \frac{\ln 2}{t_{1/2}}$$

### Formulation CP-SAT (approche déterministe)

$$\max \; \text{Eff}(C) - \lambda \cdot \text{Tox}(C)$$

Sous contraintes : dose cumulée ≤ $D_{\max}$, intervalle min entre doses, niveaux discrets, horizon borné.

### Approche stochastique (SAA)

$$\max_\pi \; \frac{1}{S} \sum_{s=1}^{S} f(\pi, \xi_s)$$

### Approche robuste (minimax)

$$\max_\pi \; \min_{s \in \mathcal{S}_{\text{adv}}} f(\pi, \xi_s)$$

## Références

- Agur et al. (1996). *Cell Proliferation*, 29(6), 359–374.
- Fiandaca et al. (2022). *Cancers*, 14(17), 4101.
- Bertsimas et al. (2016). *INFORMS Journal on Computing*.
- OR-Tools CP-SAT — https://developers.google.com/optimization/cp/cp_solver
