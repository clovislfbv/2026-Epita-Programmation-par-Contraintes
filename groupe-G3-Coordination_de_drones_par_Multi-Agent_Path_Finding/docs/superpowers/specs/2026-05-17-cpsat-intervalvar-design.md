# Design Spec — CP-SAT reformulation avec IntervalVar + AddNoOverlap
**Date:** 2026-05-17
**Auteurs:** Matteo Atkinson & Paul Witkowski
**Course:** EPITA 2026 — Programmation par Contraintes

---

## 1. Problème

Le modèle CP-SAT actuel (`solver/mapf.py`) est correct mais lent sur les scénarios moyens/grands. Cause : les contraintes d'edge conflict scalent en `O(T × N² × P × voisins_moy)`. Pour `medium_city` (8×6×3, 6 drones, T≈20) : ~216 000 contraintes de ce seul type. Le scénario `big_city` dépasse 1,4 M de contraintes.

Le notebook CSP-4 enseigne que `AddNoOverlap` est une contrainte globale beaucoup plus efficace que des paires de disjonctions manuelles. Ce spec décrit la réécriture du modèle en utilisant ce primitif.

---

## 2. Architecture

### Fichier modifié
- `solver/mapf.py` — réécriture de `MAPFSolver.solve()` uniquement. Interface (`Grid`, `Drone`, `Solution`) inchangée.

### Fichiers non modifiés
`solver/cbs.py`, `solver/od_astar.py`, `solver/astar.py`, `solver/grid.py`, `api/server.py`, frontend.

---

## 3. Nouveau modèle

### Variables

| Variable | Type | Sémantique |
|----------|------|------------|
| `here[a][p][t]` | BoolVar | Agent `a` est à la position `p` au temps `t` |
| `move[a][p][q][t]` | BoolVar | Agent `a` se déplace de `p` vers `q` au temps `t` (q peut être p pour attendre) |
| `iv_pos[a][p][t]` | OptionalIntervalVar `[t, t+1)` | Présent ssi `here[a][p][t]` |
| `iv_arc[a][e][t]` | OptionalIntervalVar `[t, t+1)` | Présent ssi agent `a` utilise l'arc non orienté `e = {p,q}` au temps `t` |

### Contraintes

**1. Unicité de position par agent**
```
AddExactlyOne(here[a][p][t] for p in positions)  ∀ a, t
```

**2. Condition initiale**
```
here[a][start_a][0] == 1  ∀ a
```

**3. Mouvement — lien here↔move**
Pour chaque agent `a`, position `p`, temps `t` :
```
here[a][p][t] == AddExactlyOne(move[a][p][q][t] for q in neighbors(p))
here[a][q][t+1] == sum(move[a][p][q][t] for p in positions if q in neighbors(p))
```
En pratique : `move[a][p][q][t]` implique `here[a][p][t]` et `here[a][q][t+1]`.

**4. Conflit vertex — AddNoOverlap par position**
```
AddNoOverlap([iv_pos[a][p][t] for all a, all t])  ∀ position p
```
Remplace les `AddAtMostOne(here[a][p][t] for a)` × P × (T+1).

**5. Conflit edge (swap) — AddNoOverlap par arc**
```
AddNoOverlap([iv_arc[a][e][t] for all a, all t])  ∀ arc non orienté e = {p,q}
```
`iv_arc[a][e][t]` est présent ssi `move[a][p][q][t] == 1` OU `move[a][q][p][t] == 1`.
Remplace les contraintes 4-littéraux `x[a][p][t] + x[b][q][t] + x[a][q][t+1] + x[b][p][t+1] <= 3`.

**6. Persistance à l'objectif** (inchangée)
```
here[a][goal_a][t+1] >= here[a][goal_a][t]  ∀ a, t
```

**7. Objectif** (inchangé)
Minimiser makespan via `arrival_vars` et `AddMaxEquality`.

### Réduction de contraintes

| Type | Avant | Après |
|------|-------|-------|
| Vertex conflict | P × (T+1) AtMostOne | P NoOverlap |
| Edge conflict | T × N(N-1)/2 × P × nbrs | E NoOverlap (E = nb arcs non orientés ≈ P × nbrs/2) |
| medium_city total edge | ~216 000 | ~360 |

### Warm-start

Les hints A* existants s'appliquent sur `here[a][p][t]` (même structure que `x[a][p][t]` actuel).

---

## 4. Tests

Les tests existants dans `tests/test_mapf.py` couvrent le comportement observable (status, paths, no-conflict, nofly). Ils doivent tous passer sans modification car l'interface `Solution` est inchangée.

---

## 5. Hors périmètre

- Réécriture de CBS, ECBS, OD-A* : hors périmètre
- Changement de l'objectif (flowtime vs makespan) : hors périmètre
- Frontend : aucun changement
