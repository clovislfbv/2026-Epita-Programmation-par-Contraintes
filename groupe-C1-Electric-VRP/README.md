# C1 — Tournées de livraison vertes (Electric VRP)

**EPITA SCIA 2026 — Programmation par Contraintes**

## Présentation

Ce projet résout l'**Electric Vehicle Routing Problem with Time Windows (EVRP-TW)** en combinant :

- **CP-SAT** (Google OR-Tools) — solveur exact avec garantie d'optimalité
- **ALNS** (Adaptive Large Neighbourhood Search) — métaheuristique pour les grandes instances

Le problème étend le VRP classique avec des contraintes d'autonomie batterie, de recharge aux bornes et de consommation énergétique variable selon la charge transportée et la pente du terrain.

## Structure du projet

```
C1-Electric-VRP/
├── C1-EVRP-Notebook.ipynb    # Notebook principal : modèle, résultats, analyse
├── data/
│   └── evrptw_instances/      # Benchmarks Schneider (2014), fichiers .txt
├── src/
│   ├── instance.py            # Modèle de données EVRP (coords, batterie, pente)
│   ├── cpsat_solver.py        # Solveur CP-SAT (AddCircuit, batterie, fenêtres)
│   ├── alns.py                # ALNS (destroy/repair, SA acceptance, poids adaptatifs)
│   └── visualization.py       # Graphiques : routes, profil batterie, comparaison
└── requirements.txt
```

## Modèle CP-SAT

### Variables

| Variable | Domaine | Signification |
|----------|---------|---------------|
| `arc[v][i][j]` | {0,1} | Véhicule v emprunte l'arc i→j |
| `load[v][i]` | [0, Q] | Charge cumulée après le nœud i |
| `bat_arrive[v][i]` | [0, B] | Batterie à l'arrivée (avant recharge) |
| `bat_depart[v][i]` | [0, B] | Batterie au départ (après recharge) |
| `bonus[v][i][j]` | [0, ⌊base_e·λ⌋] | Surcoût énergétique dû à la charge |
| `time[v][i]` | [0, T] | Heure d'arrivée au nœud i |

### Contraintes clés

- **`AddCircuit`** — circuit hamiltonien par véhicule (self-loop = nœud sauté)
- **Assignation clients** — exactement 1 véhicule par client via `Σ self_loop = K−1`
- **Batterie variable** — `bonus = ⌊base_e·λ·load/Q⌋` via `add_division_equality`
- **Recharge complète** aux stations (`bat_depart = B`)
- **Fenêtres horaires** conditionnelles via `only_enforce_if`

### Énergie variable (load-dependent)

```
e(i→j, q) = base_e[i,j] · (1 + λ · q/Q)
           = base_e[i,j] + bonus[v][i][j]
```

Le bonus est encodé en CP-SAT via `add_division_equality(bonus, C·load, Q)` où
`C = ⌊base_e·λ⌋` est une constante par arc. Pour λ=0 (instances Schneider) ou les
arcs très courts, aucune variable supplémentaire n'est créée.

### Placement optimal des bornes (mode `optimize_stations=True`)

Une variable `open_station[s] ∈ {0,1}` décide quelles bornes déployer. Les arcs
entrants/sortants d'une station fermée sont bloqués via `add_implication`. La
fonction objectif intègre un coût fixe par borne ouverte.

## ALNS

| Opérateur | Type | Description |
|-----------|------|-------------|
| `random_removal` | Destroy | Supprime k clients aléatoires |
| `worst_removal` | Destroy | Supprime les clients les plus coûteux |
| `related_removal` | Destroy | Supprime des clients géographiquement proches (Shaw) |
| `greedy_insertion` | Repair | Réinsère au meilleur coût |
| `regret_2_insertion` | Repair | Réinsère par regret-2 |

Critère d'acceptation : **simulated annealing**. Poids des opérateurs mis à jour par segment (Ropke & Pisinger 2006).

## Installation

```bash
cd C1-Electric-VRP
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook C1-EVRP-Notebook.ipynb
```

## Données benchmark (Schneider 2014)

Les fichiers texte du répertoire `data/evrptw_instances/` sont au format décrit par Schneider et al. (2014). Pour les charger en Python :

```python
from src.instance import EVRPInstance, evrptw_instances_dir

inst = EVRPInstance.from_benchmark("c101_21")   # → data/evrptw_instances/c101_21.txt
print(evrptw_instances_dir())  # chemin absolu du dossier
```

## Résultats principaux

| Instance | CP-SAT | ALNS | Gap |
|----------|--------|------|-----|
| n=5 (Schneider-like) | OPTIMAL | ≈OPTIMAL | ~0% |
| n=8 | OPTIMAL | +8–10% | faible |
| n=10 | OPTIMAL | ≈OPTIMAL | ~0% |
| n=12 | FEASIBLE (20s) | ≈OPTIMAL | faible |
| n≥15 | — (trop lent) | solution en <2s | — |

CP-SAT garantit l'optimalité jusqu'à ~10 clients sur des instances EVRP-TW.
Pour les grandes flottes, ALNS converge vers des solutions de bonne qualité en quelques secondes.

## Références

- Schneider, M., Stenger, A., & Goeke, D. (2014). *The Electric Vehicle-Routing Problem with Time Windows and Recharging Stations.* Transportation Science, 48(4), 500–520.
- Felipe, Á., et al. (2014). *A Heuristic Approach for the Green Vehicle Routing Problem.* Expert Systems with Applications, 41(14), 6424–6437.
- Ropke, S., & Pisinger, D. (2006). *An Adaptive Large Neighborhood Search Heuristic.* Transportation Science, 40(4), 455–472.
- Erdelic, T., & Caric, T. (2019). *A Survey on the Electric Vehicle Routing Problem.* Journal of Advanced Transportation.
- Data : https://data.mendeley.com/datasets/h3mrm5dhxw/1 
