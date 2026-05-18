# New Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 6 nouveaux scénarios JSON (06-11) et corriger le bug `add_building` en 2D dans `solver/grid.py`.

**Architecture:** Fix Python minimal (3 lignes) + 6 fichiers JSON autonomes. Aucune nouvelle logique. Les tests existants sont mis à jour pour refléter le nouveau compte de scénarios (5 → 11).

**Tech Stack:** Python 3, pytest, JSON

---

## File Map

| Action | Fichier | Raison |
|---|---|---|
| Modifier | `solver/grid.py` | Fix `add_building` pour grilles 2D (alts=1) |
| Modifier | `tests/test_grid.py` | Ajouter test 2D pour `add_building` |
| Modifier | `tests/test_api.py` | Mettre à jour les deux assertions `len == 5` → `len == 11` |
| Créer | `scenarios/06_dense_city.json` | Scénario 10×10×3, 10 drones, 29 bâtiments |
| Créer | `scenarios/07_bottleneck_s.json` | Scénario 10×10×1, 6 drones, 63 bâtiments |
| Créer | `scenarios/08_large_sparse.json` | Scénario 20×20×5, 10 drones, 20 bâtiments |
| Créer | `scenarios/09_large_medium.json` | Scénario 20×20×5, 15 drones, 35 bâtiments |
| Créer | `scenarios/10_large_dense.json` | Scénario 20×20×5, 20 drones, 55 bâtiments |
| Créer | `scenarios/11_mega.json` | Scénario 25×25×5, 30 drones, 80 bâtiments |

---

## Task 1 — Fix `add_building` pour grilles 2D + test

**Files:**
- Modify: `solver/grid.py:57-59`
- Modify: `tests/test_grid.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_grid.py` :

```python
def test_add_building_2d():
    g = Grid(rows=4, cols=4)          # alts=1 par défaut
    g.add_building(row=1, col=2, height=1)
    assert (1, 2) not in g.positions
    assert len(g.positions) == 15     # 16 - 1 obstacle
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
pytest tests/test_grid.py::test_add_building_2d -v
```

Attendu : **FAIL** — `(1, 2)` toujours dans `g.positions` car le bug ajoute `(1,2,0)` (3-tuple) au lieu de `(1,2)` (2-tuple).

- [ ] **Step 3 : Appliquer le fix dans `solver/grid.py`**

Remplacer la méthode `add_building` (lignes 57-59) :

```python
def add_building(self, row: int, col: int, height: int) -> None:
    if self.alts == 1:
        self.obstacles.add((row, col))
    else:
        for a in range(height):
            self.obstacles.add((row, col, a))
```

- [ ] **Step 4 : Vérifier que tous les tests passent**

```
pytest tests/test_grid.py -v
```

Attendu : **tous PASS** — le nouveau test passe, `test_add_building` (3D) toujours vert.

- [ ] **Step 5 : Commit**

```
git add solver/grid.py tests/test_grid.py
git commit -m "fix(G3): add_building gère les grilles 2D (alts=1)"
```

---

## Task 2 — Mettre à jour les tests de comptage de scénarios

**Files:**
- Modify: `tests/test_api.py:19,68`

> Ces deux assertions hardcodent `len == 5`. Après ajout des 6 nouveaux scénarios, elles passeront à 11. On les met à jour maintenant, avant de créer les fichiers JSON, pour que les tests pilotent l'implémentation.

- [ ] **Step 1 : Mettre à jour `test_get_scenarios`**

Dans `tests/test_api.py`, remplacer la ligne :
```python
    assert len(data) == 5
```
par :
```python
    assert len(data) == 11
```

- [ ] **Step 2 : Mettre à jour `test_load_all_returns_five_scenarios`**

Remplacer :
```python
def test_load_all_returns_five_scenarios():
    scenarios = load_all()
    assert len(scenarios) == 5
```
par :
```python
def test_load_all_returns_eleven_scenarios():
    scenarios = load_all()
    assert len(scenarios) == 11
```

- [ ] **Step 3 : Vérifier que ces deux tests échouent maintenant**

```
pytest tests/test_api.py::test_get_scenarios tests/test_api.py::test_load_all_returns_eleven_scenarios -v
```

Attendu : **FAIL** — il n'y a que 5 scénarios pour l'instant.

- [ ] **Step 4 : Commit**

```
git add tests/test_api.py
git commit -m "test(G3): mise à jour comptage scénarios 5→11"
```

---

## Task 3 — Scénario 06 : `dense_city`

**Files:**
- Create: `scenarios/06_dense_city.json`

- [ ] **Step 1 : Créer le fichier**

Créer `scenarios/06_dense_city.json` avec ce contenu exact :

```json
{
  "name": "dense_city",
  "description": "10×10×3 grid, 10 drones — dense 3D city with tall buildings",
  "grid": { "rows": 10, "cols": 10, "alts": 3 },
  "drones": [
    { "id": 0, "start": [0, 0, 0], "goal": [9, 9, 2] },
    { "id": 1, "start": [9, 0, 0], "goal": [0, 9, 2] },
    { "id": 2, "start": [0, 9, 1], "goal": [9, 0, 1] },
    { "id": 3, "start": [9, 9, 0], "goal": [0, 0, 2] },
    { "id": 4, "start": [0, 4, 0], "goal": [9, 5, 2] },
    { "id": 5, "start": [9, 5, 0], "goal": [0, 4, 2] },
    { "id": 6, "start": [4, 0, 0], "goal": [5, 9, 1] },
    { "id": 7, "start": [5, 9, 0], "goal": [4, 0, 2] },
    { "id": 8, "start": [0, 2, 0], "goal": [9, 7, 1] },
    { "id": 9, "start": [9, 7, 0], "goal": [0, 2, 2] }
  ],
  "buildings": [
    { "row": 3, "col": 3, "height": 3 },
    { "row": 3, "col": 7, "height": 3 },
    { "row": 7, "col": 3, "height": 3 },
    { "row": 7, "col": 7, "height": 3 },
    { "row": 1, "col": 2, "height": 2 },
    { "row": 1, "col": 5, "height": 2 },
    { "row": 1, "col": 7, "height": 2 },
    { "row": 2, "col": 1, "height": 2 },
    { "row": 2, "col": 4, "height": 2 },
    { "row": 2, "col": 8, "height": 2 },
    { "row": 3, "col": 5, "height": 2 },
    { "row": 4, "col": 2, "height": 2 },
    { "row": 4, "col": 5, "height": 2 },
    { "row": 4, "col": 8, "height": 2 },
    { "row": 5, "col": 2, "height": 2 },
    { "row": 5, "col": 4, "height": 2 },
    { "row": 5, "col": 7, "height": 2 },
    { "row": 6, "col": 2, "height": 2 },
    { "row": 6, "col": 5, "height": 2 },
    { "row": 6, "col": 8, "height": 2 },
    { "row": 7, "col": 5, "height": 2 },
    { "row": 8, "col": 1, "height": 2 },
    { "row": 8, "col": 4, "height": 2 },
    { "row": 8, "col": 7, "height": 2 },
    { "row": 2, "col": 6, "height": 1 },
    { "row": 4, "col": 7, "height": 1 },
    { "row": 5, "col": 3, "height": 1 },
    { "row": 6, "col": 4, "height": 1 },
    { "row": 8, "col": 8, "height": 1 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier que le JSON est valide et le scénario chargeable**

```
python -c "import json; d=json.load(open('scenarios/06_dense_city.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `dense_city 10 drones, 29 buildings`

- [ ] **Step 3 : Commit**

```
git add scenarios/06_dense_city.json
git commit -m "feat(G3): scénario 06 dense_city 10x10x3 — 10 drones, 29 bâtiments"
```

---

## Task 4 — Scénario 07 : `bottleneck_s`

**Files:**
- Create: `scenarios/07_bottleneck_s.json`

> Tunnel en S creusé dans un bloc massif. 63 bâtiments (height 1) remplissent tout sauf le tunnel. Le fix Task 1 est requis pour que ces bâtiments aient un effet en grille 2D (alts=1).

- [ ] **Step 1 : Créer le fichier**

Créer `scenarios/07_bottleneck_s.json` avec ce contenu exact :

```json
{
  "name": "bottleneck_s",
  "description": "10×10×1 grid, 6 drones — S-tunnel carved into solid block, bidirectional conflict",
  "grid": { "rows": 10, "cols": 10, "alts": 1 },
  "drones": [
    { "id": 0, "start": [0, 0], "goal": [8, 9] },
    { "id": 1, "start": [0, 1], "goal": [9, 9] },
    { "id": 2, "start": [1, 0], "goal": [9, 8] },
    { "id": 3, "start": [8, 9], "goal": [0, 0] },
    { "id": 4, "start": [9, 9], "goal": [0, 1] },
    { "id": 5, "start": [9, 8], "goal": [1, 0] }
  ],
  "buildings": [
    { "row": 0, "col": 2, "height": 1 },
    { "row": 0, "col": 3, "height": 1 },
    { "row": 0, "col": 4, "height": 1 },
    { "row": 0, "col": 5, "height": 1 },
    { "row": 0, "col": 6, "height": 1 },
    { "row": 0, "col": 7, "height": 1 },
    { "row": 0, "col": 8, "height": 1 },
    { "row": 0, "col": 9, "height": 1 },
    { "row": 1, "col": 2, "height": 1 },
    { "row": 1, "col": 3, "height": 1 },
    { "row": 1, "col": 4, "height": 1 },
    { "row": 1, "col": 5, "height": 1 },
    { "row": 1, "col": 6, "height": 1 },
    { "row": 1, "col": 7, "height": 1 },
    { "row": 1, "col": 8, "height": 1 },
    { "row": 1, "col": 9, "height": 1 },
    { "row": 2, "col": 7, "height": 1 },
    { "row": 2, "col": 8, "height": 1 },
    { "row": 2, "col": 9, "height": 1 },
    { "row": 3, "col": 0, "height": 1 },
    { "row": 3, "col": 1, "height": 1 },
    { "row": 3, "col": 2, "height": 1 },
    { "row": 3, "col": 3, "height": 1 },
    { "row": 3, "col": 4, "height": 1 },
    { "row": 3, "col": 5, "height": 1 },
    { "row": 3, "col": 7, "height": 1 },
    { "row": 3, "col": 8, "height": 1 },
    { "row": 3, "col": 9, "height": 1 },
    { "row": 4, "col": 0, "height": 1 },
    { "row": 4, "col": 1, "height": 1 },
    { "row": 4, "col": 2, "height": 1 },
    { "row": 4, "col": 3, "height": 1 },
    { "row": 4, "col": 4, "height": 1 },
    { "row": 4, "col": 5, "height": 1 },
    { "row": 4, "col": 7, "height": 1 },
    { "row": 4, "col": 8, "height": 1 },
    { "row": 4, "col": 9, "height": 1 },
    { "row": 5, "col": 0, "height": 1 },
    { "row": 5, "col": 1, "height": 1 },
    { "row": 5, "col": 2, "height": 1 },
    { "row": 5, "col": 7, "height": 1 },
    { "row": 5, "col": 8, "height": 1 },
    { "row": 5, "col": 9, "height": 1 },
    { "row": 6, "col": 0, "height": 1 },
    { "row": 6, "col": 1, "height": 1 },
    { "row": 6, "col": 2, "height": 1 },
    { "row": 6, "col": 4, "height": 1 },
    { "row": 6, "col": 5, "height": 1 },
    { "row": 6, "col": 6, "height": 1 },
    { "row": 6, "col": 7, "height": 1 },
    { "row": 6, "col": 8, "height": 1 },
    { "row": 6, "col": 9, "height": 1 },
    { "row": 7, "col": 0, "height": 1 },
    { "row": 7, "col": 1, "height": 1 },
    { "row": 7, "col": 2, "height": 1 },
    { "row": 8, "col": 0, "height": 1 },
    { "row": 8, "col": 1, "height": 1 },
    { "row": 8, "col": 2, "height": 1 },
    { "row": 8, "col": 3, "height": 1 },
    { "row": 9, "col": 0, "height": 1 },
    { "row": 9, "col": 1, "height": 1 },
    { "row": 9, "col": 2, "height": 1 },
    { "row": 9, "col": 3, "height": 1 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier JSON et compter les bâtiments**

```
python -c "import json; d=json.load(open('scenarios/07_bottleneck_s.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `bottleneck_s 6 drones, 63 buildings`

- [ ] **Step 3 : Vérifier que le tunnel est correct (aucun start/goal n'est bloqué)**

```python
python -c "
import json
from solver.grid import Grid
d = json.load(open('scenarios/07_bottleneck_s.json'))
g = Grid(**d['grid'])
for b in d['buildings']:
    g.add_building(b['row'], b['col'], b['height'])
starts = [tuple(dr['start']) for dr in d['drones']]
goals  = [tuple(dr['goal'])  for dr in d['drones']]
blocked = g.obstacles | g._nofly
for p in starts + goals:
    assert p not in blocked, f'{p} is blocked!'
print('All starts/goals are free. Free cells:', len(g.positions))
"
```

Attendu : `All starts/goals are free. Free cells: 37`

- [ ] **Step 4 : Commit**

```
git add scenarios/07_bottleneck_s.json
git commit -m "feat(G3): scénario 07 bottleneck_s 10x10x1 — tunnel S dans bloc plein"
```

---

## Task 5 — Scénario 08 : `large_sparse`

**Files:**
- Create: `scenarios/08_large_sparse.json`

- [ ] **Step 1 : Créer le fichier**

```json
{
  "name": "large_sparse",
  "description": "20×20×5 grid, 10 drones — large grid, sparse obstacles (scalability baseline)",
  "grid": { "rows": 20, "cols": 20, "alts": 5 },
  "drones": [
    { "id": 0,  "start": [0,  0,  0], "goal": [19, 19, 4] },
    { "id": 1,  "start": [19, 0,  0], "goal": [0,  19, 4] },
    { "id": 2,  "start": [0,  19, 1], "goal": [19, 0,  1] },
    { "id": 3,  "start": [19, 19, 0], "goal": [0,  0,  4] },
    { "id": 4,  "start": [0,  9,  0], "goal": [19, 10, 4] },
    { "id": 5,  "start": [19, 10, 0], "goal": [0,  9,  4] },
    { "id": 6,  "start": [9,  0,  0], "goal": [10, 19, 2] },
    { "id": 7,  "start": [10, 19, 0], "goal": [9,  0,  4] },
    { "id": 8,  "start": [0,  4,  0], "goal": [19, 15, 3] },
    { "id": 9,  "start": [19, 15, 0], "goal": [0,  4,  3] }
  ],
  "buildings": [
    { "row": 3,  "col": 3,  "height": 3 },
    { "row": 3,  "col": 10, "height": 3 },
    { "row": 3,  "col": 16, "height": 2 },
    { "row": 7,  "col": 5,  "height": 4 },
    { "row": 7,  "col": 13, "height": 3 },
    { "row": 10, "col": 3,  "height": 3 },
    { "row": 10, "col": 10, "height": 4 },
    { "row": 10, "col": 17, "height": 3 },
    { "row": 13, "col": 6,  "height": 3 },
    { "row": 13, "col": 14, "height": 4 },
    { "row": 16, "col": 3,  "height": 2 },
    { "row": 16, "col": 10, "height": 3 },
    { "row": 16, "col": 16, "height": 3 },
    { "row": 5,  "col": 8,  "height": 3 },
    { "row": 5,  "col": 16, "height": 2 },
    { "row": 12, "col": 8,  "height": 3 },
    { "row": 9,  "col": 16, "height": 4 },
    { "row": 8,  "col": 2,  "height": 3 },
    { "row": 2,  "col": 12, "height": 2 },
    { "row": 17, "col": 8,  "height": 3 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier**

```
python -c "import json; d=json.load(open('scenarios/08_large_sparse.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `large_sparse 10 drones, 20 buildings`

- [ ] **Step 3 : Commit**

```
git add scenarios/08_large_sparse.json
git commit -m "feat(G3): scénario 08 large_sparse 20x20x5 — 10 drones, 20 bâtiments"
```

---

## Task 6 — Scénario 09 : `large_medium`

**Files:**
- Create: `scenarios/09_large_medium.json`

> Reprend les 10 drones de 08 + 5 nouveaux, et les 20 bâtiments de 08 + 15 nouveaux.

- [ ] **Step 1 : Créer le fichier**

```json
{
  "name": "large_medium",
  "description": "20×20×5 grid, 15 drones — large grid, medium obstacles (scalability mid)",
  "grid": { "rows": 20, "cols": 20, "alts": 5 },
  "drones": [
    { "id": 0,  "start": [0,  0,  0], "goal": [19, 19, 4] },
    { "id": 1,  "start": [19, 0,  0], "goal": [0,  19, 4] },
    { "id": 2,  "start": [0,  19, 1], "goal": [19, 0,  1] },
    { "id": 3,  "start": [19, 19, 0], "goal": [0,  0,  4] },
    { "id": 4,  "start": [0,  9,  0], "goal": [19, 10, 4] },
    { "id": 5,  "start": [19, 10, 0], "goal": [0,  9,  4] },
    { "id": 6,  "start": [9,  0,  0], "goal": [10, 19, 2] },
    { "id": 7,  "start": [10, 19, 0], "goal": [9,  0,  4] },
    { "id": 8,  "start": [0,  4,  0], "goal": [19, 15, 3] },
    { "id": 9,  "start": [19, 15, 0], "goal": [0,  4,  3] },
    { "id": 10, "start": [0,  14, 0], "goal": [19, 5,  2] },
    { "id": 11, "start": [19, 5,  0], "goal": [0,  14, 2] },
    { "id": 12, "start": [4,  0,  0], "goal": [15, 19, 1] },
    { "id": 13, "start": [15, 19, 0], "goal": [4,  0,  3] },
    { "id": 14, "start": [7,  19, 2], "goal": [12, 0,  2] }
  ],
  "buildings": [
    { "row": 3,  "col": 3,  "height": 3 },
    { "row": 3,  "col": 10, "height": 3 },
    { "row": 3,  "col": 16, "height": 2 },
    { "row": 7,  "col": 5,  "height": 4 },
    { "row": 7,  "col": 13, "height": 3 },
    { "row": 10, "col": 3,  "height": 3 },
    { "row": 10, "col": 10, "height": 4 },
    { "row": 10, "col": 17, "height": 3 },
    { "row": 13, "col": 6,  "height": 3 },
    { "row": 13, "col": 14, "height": 4 },
    { "row": 16, "col": 3,  "height": 2 },
    { "row": 16, "col": 10, "height": 3 },
    { "row": 16, "col": 16, "height": 3 },
    { "row": 5,  "col": 8,  "height": 3 },
    { "row": 5,  "col": 16, "height": 2 },
    { "row": 12, "col": 8,  "height": 3 },
    { "row": 9,  "col": 16, "height": 4 },
    { "row": 8,  "col": 2,  "height": 3 },
    { "row": 2,  "col": 12, "height": 2 },
    { "row": 17, "col": 8,  "height": 3 },
    { "row": 4,  "col": 6,  "height": 4 },
    { "row": 4,  "col": 14, "height": 3 },
    { "row": 6,  "col": 10, "height": 4 },
    { "row": 6,  "col": 18, "height": 3 },
    { "row": 8,  "col": 6,  "height": 4 },
    { "row": 9,  "col": 12, "height": 3 },
    { "row": 11, "col": 5,  "height": 4 },
    { "row": 11, "col": 15, "height": 3 },
    { "row": 14, "col": 4,  "height": 4 },
    { "row": 14, "col": 11, "height": 3 },
    { "row": 15, "col": 7,  "height": 4 },
    { "row": 2,  "col": 5,  "height": 3 },
    { "row": 2,  "col": 17, "height": 3 },
    { "row": 18, "col": 5,  "height": 3 },
    { "row": 18, "col": 14, "height": 3 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier**

```
python -c "import json; d=json.load(open('scenarios/09_large_medium.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `large_medium 15 drones, 35 buildings`

- [ ] **Step 3 : Commit**

```
git add scenarios/09_large_medium.json
git commit -m "feat(G3): scénario 09 large_medium 20x20x5 — 15 drones, 35 bâtiments"
```

---

## Task 7 — Scénario 10 : `large_dense`

**Files:**
- Create: `scenarios/10_large_dense.json`

> 20 drones (15 de 09 + 5 nouveaux), 55 bâtiments (35 de 09 + 20 nouveaux dont height 5).
> height=5 avec alts=5 bloque TOUS les niveaux d'altitude → cellule infranchissable.

- [ ] **Step 1 : Créer le fichier**

```json
{
  "name": "large_dense",
  "description": "20×20×5 grid, 20 drones — large grid, dense obstacles with impassable towers",
  "grid": { "rows": 20, "cols": 20, "alts": 5 },
  "drones": [
    { "id": 0,  "start": [0,  0,  0], "goal": [19, 19, 4] },
    { "id": 1,  "start": [19, 0,  0], "goal": [0,  19, 4] },
    { "id": 2,  "start": [0,  19, 1], "goal": [19, 0,  1] },
    { "id": 3,  "start": [19, 19, 0], "goal": [0,  0,  4] },
    { "id": 4,  "start": [0,  9,  0], "goal": [19, 10, 4] },
    { "id": 5,  "start": [19, 10, 0], "goal": [0,  9,  4] },
    { "id": 6,  "start": [9,  0,  0], "goal": [10, 19, 2] },
    { "id": 7,  "start": [10, 19, 0], "goal": [9,  0,  4] },
    { "id": 8,  "start": [0,  4,  0], "goal": [19, 15, 3] },
    { "id": 9,  "start": [19, 15, 0], "goal": [0,  4,  3] },
    { "id": 10, "start": [0,  14, 0], "goal": [19, 5,  2] },
    { "id": 11, "start": [19, 5,  0], "goal": [0,  14, 2] },
    { "id": 12, "start": [4,  0,  0], "goal": [15, 19, 1] },
    { "id": 13, "start": [15, 19, 0], "goal": [4,  0,  3] },
    { "id": 14, "start": [7,  19, 2], "goal": [12, 0,  2] },
    { "id": 15, "start": [0,  7,  0], "goal": [19, 12, 4] },
    { "id": 16, "start": [19, 12, 0], "goal": [0,  7,  4] },
    { "id": 17, "start": [3,  0,  1], "goal": [16, 19, 3] },
    { "id": 18, "start": [16, 19, 1], "goal": [3,  0,  3] },
    { "id": 19, "start": [2,  0,  0], "goal": [17, 19, 4] }
  ],
  "buildings": [
    { "row": 3,  "col": 3,  "height": 3 },
    { "row": 3,  "col": 10, "height": 3 },
    { "row": 3,  "col": 16, "height": 2 },
    { "row": 7,  "col": 5,  "height": 4 },
    { "row": 7,  "col": 13, "height": 3 },
    { "row": 10, "col": 3,  "height": 3 },
    { "row": 10, "col": 10, "height": 4 },
    { "row": 10, "col": 17, "height": 3 },
    { "row": 13, "col": 6,  "height": 3 },
    { "row": 13, "col": 14, "height": 4 },
    { "row": 16, "col": 3,  "height": 2 },
    { "row": 16, "col": 10, "height": 3 },
    { "row": 16, "col": 16, "height": 3 },
    { "row": 5,  "col": 8,  "height": 3 },
    { "row": 5,  "col": 16, "height": 2 },
    { "row": 12, "col": 8,  "height": 3 },
    { "row": 9,  "col": 16, "height": 4 },
    { "row": 8,  "col": 2,  "height": 3 },
    { "row": 2,  "col": 12, "height": 2 },
    { "row": 17, "col": 8,  "height": 3 },
    { "row": 4,  "col": 6,  "height": 4 },
    { "row": 4,  "col": 14, "height": 3 },
    { "row": 6,  "col": 10, "height": 4 },
    { "row": 6,  "col": 18, "height": 3 },
    { "row": 8,  "col": 6,  "height": 4 },
    { "row": 9,  "col": 12, "height": 3 },
    { "row": 11, "col": 5,  "height": 4 },
    { "row": 11, "col": 15, "height": 3 },
    { "row": 14, "col": 4,  "height": 4 },
    { "row": 14, "col": 11, "height": 3 },
    { "row": 15, "col": 7,  "height": 4 },
    { "row": 2,  "col": 5,  "height": 3 },
    { "row": 2,  "col": 17, "height": 3 },
    { "row": 18, "col": 5,  "height": 3 },
    { "row": 18, "col": 14, "height": 3 },
    { "row": 1,  "col": 6,  "height": 5 },
    { "row": 1,  "col": 12, "height": 4 },
    { "row": 3,  "col": 18, "height": 4 },
    { "row": 5,  "col": 3,  "height": 5 },
    { "row": 5,  "col": 14, "height": 4 },
    { "row": 7,  "col": 8,  "height": 5 },
    { "row": 7,  "col": 16, "height": 4 },
    { "row": 9,  "col": 4,  "height": 5 },
    { "row": 9,  "col": 7,  "height": 4 },
    { "row": 11, "col": 9,  "height": 5 },
    { "row": 11, "col": 17, "height": 4 },
    { "row": 13, "col": 2,  "height": 5 },
    { "row": 13, "col": 17, "height": 4 },
    { "row": 15, "col": 12, "height": 5 },
    { "row": 15, "col": 16, "height": 4 },
    { "row": 17, "col": 3,  "height": 5 },
    { "row": 17, "col": 11, "height": 4 },
    { "row": 18, "col": 17, "height": 5 },
    { "row": 6,  "col": 5,  "height": 4 },
    { "row": 12, "col": 13, "height": 4 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier**

```
python -c "import json; d=json.load(open('scenarios/10_large_dense.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `large_dense 20 drones, 55 buildings`

- [ ] **Step 3 : Commit**

```
git add scenarios/10_large_dense.json
git commit -m "feat(G3): scénario 10 large_dense 20x20x5 — 20 drones, 55 bâtiments"
```

---

## Task 8 — Scénario 11 : `mega`

**Files:**
- Create: `scenarios/11_mega.json`

- [ ] **Step 1 : Créer le fichier**

```json
{
  "name": "mega",
  "description": "25×25×5 grid, 30 drones — stress test with massive obstacle field",
  "grid": { "rows": 25, "cols": 25, "alts": 5 },
  "drones": [
    { "id": 0,  "start": [0,  0,  0], "goal": [24, 24, 4] },
    { "id": 1,  "start": [24, 0,  0], "goal": [0,  24, 4] },
    { "id": 2,  "start": [0,  24, 1], "goal": [24, 0,  1] },
    { "id": 3,  "start": [24, 24, 0], "goal": [0,  0,  4] },
    { "id": 4,  "start": [0,  6,  0], "goal": [24, 18, 3] },
    { "id": 5,  "start": [0,  12, 0], "goal": [24, 12, 4] },
    { "id": 6,  "start": [0,  18, 0], "goal": [24, 6,  3] },
    { "id": 7,  "start": [24, 6,  0], "goal": [0,  18, 3] },
    { "id": 8,  "start": [24, 12, 0], "goal": [0,  12, 4] },
    { "id": 9,  "start": [24, 18, 0], "goal": [0,  6,  3] },
    { "id": 10, "start": [6,  0,  0], "goal": [18, 24, 2] },
    { "id": 11, "start": [12, 0,  0], "goal": [12, 24, 2] },
    { "id": 12, "start": [18, 0,  0], "goal": [6,  24, 2] },
    { "id": 13, "start": [6,  24, 0], "goal": [18, 0,  2] },
    { "id": 14, "start": [12, 24, 0], "goal": [12, 0,  4] },
    { "id": 15, "start": [18, 24, 0], "goal": [6,  0,  4] },
    { "id": 16, "start": [0,  3,  0], "goal": [24, 21, 2] },
    { "id": 17, "start": [0,  21, 0], "goal": [24, 3,  2] },
    { "id": 18, "start": [24, 3,  0], "goal": [0,  21, 2] },
    { "id": 19, "start": [24, 21, 0], "goal": [0,  3,  2] },
    { "id": 20, "start": [3,  0,  1], "goal": [21, 24, 3] },
    { "id": 21, "start": [21, 0,  1], "goal": [3,  24, 3] },
    { "id": 22, "start": [3,  24, 1], "goal": [21, 0,  3] },
    { "id": 23, "start": [21, 24, 1], "goal": [3,  0,  3] },
    { "id": 24, "start": [0,  9,  2], "goal": [24, 15, 4] },
    { "id": 25, "start": [0,  15, 2], "goal": [24, 9,  4] },
    { "id": 26, "start": [9,  0,  2], "goal": [15, 24, 4] },
    { "id": 27, "start": [15, 0,  2], "goal": [9,  24, 4] },
    { "id": 28, "start": [9,  24, 2], "goal": [15, 0,  0] },
    { "id": 29, "start": [15, 24, 2], "goal": [9,  0,  0] }
  ],
  "buildings": [
    { "row": 5,  "col": 5,  "height": 5 },
    { "row": 5,  "col": 19, "height": 5 },
    { "row": 10, "col": 10, "height": 5 },
    { "row": 14, "col": 5,  "height": 5 },
    { "row": 14, "col": 19, "height": 5 },
    { "row": 19, "col": 14, "height": 5 },
    { "row": 8,  "col": 17, "height": 5 },
    { "row": 17, "col": 8,  "height": 5 },
    { "row": 11, "col": 2,  "height": 5 },
    { "row": 2,  "col": 11, "height": 5 },
    { "row": 2,  "col": 5,  "height": 4 },
    { "row": 2,  "col": 14, "height": 4 },
    { "row": 2,  "col": 20, "height": 4 },
    { "row": 5,  "col": 10, "height": 4 },
    { "row": 5,  "col": 15, "height": 4 },
    { "row": 8,  "col": 3,  "height": 4 },
    { "row": 8,  "col": 8,  "height": 4 },
    { "row": 8,  "col": 20, "height": 4 },
    { "row": 10, "col": 5,  "height": 4 },
    { "row": 10, "col": 17, "height": 4 },
    { "row": 11, "col": 12, "height": 4 },
    { "row": 11, "col": 20, "height": 4 },
    { "row": 13, "col": 3,  "height": 4 },
    { "row": 13, "col": 8,  "height": 4 },
    { "row": 14, "col": 12, "height": 4 },
    { "row": 14, "col": 16, "height": 4 },
    { "row": 16, "col": 5,  "height": 4 },
    { "row": 17, "col": 16, "height": 4 },
    { "row": 17, "col": 20, "height": 4 },
    { "row": 19, "col": 3,  "height": 4 },
    { "row": 19, "col": 8,  "height": 4 },
    { "row": 20, "col": 11, "height": 4 },
    { "row": 20, "col": 16, "height": 4 },
    { "row": 22, "col": 5,  "height": 4 },
    { "row": 22, "col": 19, "height": 4 },
    { "row": 3,  "col": 3,  "height": 3 },
    { "row": 3,  "col": 17, "height": 3 },
    { "row": 4,  "col": 9,  "height": 3 },
    { "row": 4,  "col": 22, "height": 3 },
    { "row": 6,  "col": 6,  "height": 3 },
    { "row": 6,  "col": 12, "height": 3 },
    { "row": 7,  "col": 19, "height": 3 },
    { "row": 9,  "col": 2,  "height": 3 },
    { "row": 9,  "col": 14, "height": 3 },
    { "row": 10, "col": 22, "height": 3 },
    { "row": 12, "col": 6,  "height": 3 },
    { "row": 12, "col": 18, "height": 3 },
    { "row": 13, "col": 15, "height": 3 },
    { "row": 15, "col": 3,  "height": 3 },
    { "row": 15, "col": 10, "height": 3 },
    { "row": 15, "col": 22, "height": 3 },
    { "row": 16, "col": 17, "height": 3 },
    { "row": 18, "col": 5,  "height": 3 },
    { "row": 18, "col": 12, "height": 3 },
    { "row": 19, "col": 21, "height": 3 },
    { "row": 20, "col": 3,  "height": 3 },
    { "row": 21, "col": 8,  "height": 3 },
    { "row": 21, "col": 17, "height": 3 },
    { "row": 22, "col": 11, "height": 3 },
    { "row": 23, "col": 15, "height": 3 },
    { "row": 1,  "col": 8,  "height": 2 },
    { "row": 1,  "col": 16, "height": 2 },
    { "row": 3,  "col": 22, "height": 2 },
    { "row": 4,  "col": 4,  "height": 2 },
    { "row": 6,  "col": 20, "height": 2 },
    { "row": 7,  "col": 11, "height": 2 },
    { "row": 9,  "col": 7,  "height": 2 },
    { "row": 9,  "col": 18, "height": 2 },
    { "row": 12, "col": 3,  "height": 2 },
    { "row": 12, "col": 14, "height": 2 },
    { "row": 13, "col": 21, "height": 2 },
    { "row": 16, "col": 9,  "height": 2 },
    { "row": 17, "col": 4,  "height": 2 },
    { "row": 18, "col": 19, "height": 2 },
    { "row": 19, "col": 17, "height": 2 },
    { "row": 20, "col": 22, "height": 2 },
    { "row": 21, "col": 2,  "height": 2 },
    { "row": 21, "col": 14, "height": 2 },
    { "row": 23, "col": 6,  "height": 2 },
    { "row": 23, "col": 20, "height": 2 }
  ],
  "nofly": []
}
```

- [ ] **Step 2 : Vérifier**

```
python -c "import json; d=json.load(open('scenarios/11_mega.json')); print(d['name'], len(d['drones']), 'drones,', len(d['buildings']), 'buildings')"
```

Attendu : `mega 30 drones, 80 buildings`

- [ ] **Step 3 : Commit**

```
git add scenarios/11_mega.json
git commit -m "feat(G3): scénario 11 mega 25x25x5 — 30 drones, 80 bâtiments"
```

---

## Task 9 — Vérification finale : tous les tests passent

**Files:**
- Modify: aucun (vérification uniquement)

- [ ] **Step 1 : Lancer la suite complète**

```
pytest tests/ -v
```

Attendu : **tous PASS**. En particulier :
- `test_add_building_2d` : PASS (fix Task 1)
- `test_load_all_returns_eleven_scenarios` : PASS (11 JSON dans `scenarios/`)
- `test_get_scenarios` → `len(data) == 11` : PASS
- `test_add_building` (3D existant) : PASS (comportement inchangé)

- [ ] **Step 2 : Vérifier que chaque scénario a les clés requises**

```
python -c "
from api.scenario_loader import load_all
scenarios = load_all()
print(f'Total scenarios: {len(scenarios)}')
for s in scenarios:
    assert 'name' in s and 'grid' in s and 'drones' in s and 'buildings' in s
    print(f'  {s[\"name\"]}: {s[\"grid\"][\"rows\"]}x{s[\"grid\"][\"cols\"]}x{s[\"grid\"][\"alts\"]}, {len(s[\"drones\"])} drones, {len(s[\"buildings\"])} buildings')
print('All OK')
"
```

Attendu :
```
Total scenarios: 11
  micro_flat: 4x4x1, 3 drones, 0 buildings
  micro_3d: 4x4x3, 4 drones, 2 buildings
  medium_flat: 6x8x1, 5 drones, 0 buildings
  medium_city: 8x6x3, 6 drones, 3 buildings
  big_city: 10x10x3, 8 drones, 6 buildings
  dense_city: 10x10x3, 10 drones, 29 buildings
  bottleneck_s: 10x10x1, 6 drones, 63 buildings
  large_sparse: 20x20x5, 10 drones, 20 buildings
  large_medium: 20x20x5, 15 drones, 35 buildings
  large_dense: 20x20x5, 20 drones, 55 buildings
  mega: 25x25x5, 30 drones, 80 buildings
All OK
```

- [ ] **Step 3 : Commit final**

```
git add -A
git commit -m "feat(G3): 6 nouveaux scénarios 06-11 + fix add_building 2D — implémentation complète"
```
