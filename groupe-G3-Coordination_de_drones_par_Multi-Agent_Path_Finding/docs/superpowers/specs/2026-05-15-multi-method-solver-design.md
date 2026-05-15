# Design Spec — Multi-Method MAPF Solver
**Date:** 2026-05-15
**Authors:** Matteo Atkinson & Paul Witkowski
**Course:** EPITA 2026 — Programmation par Contraintes

---

## 1. Problème

Le scénario `05_big_city` (10×10×3, 8 drones) dépasse le temps limite du solveur CP-SAT monolithique. La cause : les contraintes de conflits d'arêtes scalent en O(T × N² × P × voisins_moy), soit ~1,4 million de contraintes pour ce scénario.

Le README du cours demande explicitement de comparer avec les algorithmes spécialisés MAPF : CBS, A* with OD, ECBS. Ce spec décrit l'ajout de ces trois méthodes en parallèle du CP-SAT existant, avec une sélection via dropdown dans le frontend.

---

## 2. Architecture

### Nouveaux fichiers

```
solver/
  cbs.py       # CBSSolver + ECBSSolver (ECBS = CBS avec focal search)
  od_astar.py  # ODAstarSolver (A* with Operator Decomposition)
```

### Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/server.py` | Dispatch vers le bon solver selon le champ `method` du body |
| `frontend/index.html` | Dropdown "Méthode" dans la barre de contrôles + HUD |

### Fichiers non modifiés

`solver/mapf.py`, `solver/grid.py`, `solver/astar.py` — intacts.

### Interface commune

Tous les solvers reçoivent `(grid: Grid, drones: List[Drone], time_limit_s: float)` et retournent un objet `Solution` existant. Le frontend ne change pas côté parsing.

---

## 3. Algorithmes

### 3.1 CBS — Conflict-Based Search

Deux niveaux de recherche :

**Haut niveau — Arbre de contraintes (CT)**

Chaque nœud du CT contient :
- Un ensemble de contraintes `{(agent, pos, t)}` — l'agent ne peut pas être en `pos` au temps `t`
- Les chemins individuels calculés sous ces contraintes
- Le coût = somme des longueurs de chemin

```
nœud racine : A* individuel pour chaque agent, sans contraintes
boucle OPEN (min-heap sur coût) :
  nœud = pop()
  détecter le premier conflit (vertex ou edge)
  si aucun conflit → SOLUTION TROUVÉE (somme de chemins optimale)
  conflit (agent_a, agent_b, pos, t) :
    fils A : contraintes ∪ {(agent_a, pos, t)} → re-solver A* pour agent_a
    fils B : contraintes ∪ {(agent_b, pos, t)} → re-solver A* pour agent_b
    pousser fils A et fils B dans OPEN
```

**Bas niveau — A* space-time**

Extension de `astar.py` avec une dimension temporelle et un ensemble de contraintes à éviter. L'état = `(pos, t)`. Si `(agent, pos, t)` est contraint, la position est exclue à ce timestep.

**Conflits détectés :**
- Vertex conflict : deux agents à la même position au même temps
- Edge conflict (swap) : agents a et b échangent leurs positions entre t et t+1

### 3.2 ECBS — Enhanced CBS

Identique à CBS avec **focal search** :

- `f_min` = coût du meilleur nœud dans OPEN
- `FOCAL` = sous-ensemble de OPEN où coût ≤ `w × f_min`
- On choisit dans FOCAL le nœud avec le **moins de conflits** (heuristique inadmissible)

Paramètre `w` (défaut 1.3) : solution garantie ≤ `w × optimal`. Plus `w` est grand, plus c'est rapide mais sous-optimal.

Implémenté dans `cbs.py`, même classe `CBSSolver` avec paramètre `w` (`w=1.0` = CBS exact).

### 3.3 A\* with Operator Decomposition

A\* sur l'espace joint multi-agent avec décomposition des opérateurs :

**État standard** : `(pos_0, pos_1, ..., pos_N-1)` — toutes positions au même temps

**Operator Decomposition** : on déplace les agents un par un dans un ordre fixe. Les états "intermédiaires" (agents 0..k déjà bougés, agents k+1..N-1 pas encore) sont des nœuds valides dans l'espace de recherche. Cela réduit le branching factor de `|moves|^N` à `|moves|` par étape intermédiaire.

**Heuristique** : somme des distances A* individuelles (admissible, calcul en prétraitement).

**Contraintes** : vertex et edge conflicts vérifiés lors de la génération des successeurs.

Optimal mais complexité mémoire croît avec N — adapté jusqu'à N ≈ 6-7 agents.

---

## 4. Contrat API

### `POST /solve` — champs ajoutés

```json
{
  "grid": { "rows": 10, "cols": 10, "alts": 3 },
  "drones": [...],
  "buildings": [...],
  "nofly": [],
  "time_limit_s": 30,
  "method": "cpsat",
  "suboptimality_w": 1.3
}
```

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `method` | string | `"cpsat"` | `"cpsat"` \| `"cbs"` \| `"ecbs"` \| `"od_astar"` |
| `suboptimality_w` | float | `1.3` | Facteur ECBS uniquement, ignoré sinon |

### Response — champ ajouté

```json
{
  "status": "optimal",
  "method": "cbs",
  "makespan": 24,
  "solve_time_ms": 340,
  "conflicts_avoided": 7,
  "paths": { "0": [[0,0,0], ...], ... }
}
```

---

## 5. Frontend

### Dropdown méthode

Ajout dans la barre de contrôles de `index.html`, entre "Solve" et "Play" :

```html
<select id="sel-method">
  <option value="cpsat">CP-SAT optimal</option>
  <option value="cbs">CBS (optimal)</option>
  <option value="ecbs">ECBS (rapide, ×1.3)</option>
  <option value="od_astar">A* OD (optimal)</option>
</select>
```

La valeur sélectionnée est incluse dans le body POST de `fetchSolve`.

### HUD — ligne ajoutée

```
Méthode: <span id="h-method">—</span>
```

Affiche la méthode retournée par l'API après chaque solve.

### Aucun autre changement frontend

Le parsing de `paths` reste identique. `DroneManager`, `CityScene`, `UIManager` non modifiés.

---

## 6. Comparaison des méthodes

| Méthode | Optimalité | Vitesse sur big_city | Remarque |
|---------|-----------|---------------------|----------|
| CP-SAT | Optimale | Timeout (>50s) | Modèle monolithique, scaling quadratique |
| CBS | Optimale (somme de coûts) | ~1-5s | Optimal si peu de conflits |
| ECBS | ≤ 1.3 × optimal | <1s | Recommandé pour la démo |
| A\* OD | Optimale | Variable | Lent si N > 6 |

**Note :** CBS et ECBS minimisent la **somme des longueurs de chemin** (flow time), pas le makespan. CP-SAT et A\* OD minimisent le makespan. Les résultats sont comparables mais pas identiques.

---

## 7. Hors scope

- Modification de l'objectif CP-SAT (reste makespan)
- Support multi-objectif
- Persistance des résultats de comparaison
- Tests de performance automatisés entre méthodes
