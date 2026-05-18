# Design — Cleanup, corrections et optimisations (2026-05-17)

## Contexte

Cinq tâches indépendantes sur le projet MAPF G3 :
suppression d'une fonctionnalité obsolète, correction d'un bug visuel,
optimisations des solveurs, correction d'un bug de timeout, et réécriture
d'historique git.

---

## Tâche 1 — Suppression complète des no-fly zones

### Périmètre

La fonctionnalité no-fly (zones interdites interactives) est retirée intégralement.
Elle n'est pas utilisée dans les scénarios et alourdit l'interface sans apport
pédagogique.

### Fichiers et suppressions

| Fichier | Suppressions |
|---|---|
| `solver/grid.py` | Champ `_nofly: Set[Pos]`, méthodes `add_nofly_box` et `clear_nofly`, union `self._nofly` dans `positions` et `neighbors` |
| `api/server.py` | Boucle `for nf in body.get("nofly", [])` |
| `frontend/scene.js` | Champ `_noFlyMeshes`, méthodes `addNoFlyBox` et `clearNoFly` |
| `frontend/ui.js` | Champs `_nofly`, `_placingNoFly`, `_btnNF` ; handlers no-fly ; méthodes `addNoFlyFromClick`, `getNoFly` ; paramètres `onAddNoFly`/`onClearNoFly` du constructeur |
| `frontend/index.html` | Boutons `#btn-nofly` et `#btn-clear-nofly`, CSS associé (sélecteurs `#btn-nofly`, `#btn-clear-nofly`, `.is-active`), raycaster de placement, callbacks `onAddNoFly`/`onClearNoFly` dans l'objet UIManager |
| `scenarios/*.json` | Clé `"nofly": []` dans chaque fichier JSON |

### Comportement après suppression

- La grille Grid ne possède plus qu'un seul ensemble d'obstacles : `obstacles`.
- Le serveur ignore tout champ `nofly` dans le body (il n'est plus envoyé).
- L'interface n'expose plus aucun contrôle no-fly.

---

## Tâche 2 — Correction du scénario bottleneck (visuel + solveur)

### Cause racine du bug visuel

Les buildings et les drones sont positionnés aux **intersections de la grille**
(coordonnées entières) et non aux **centres de cellule** (entier + 0,5).
La grille visuelle (lignes à x=0,1,2,…) définit la cellule (r,c) comme occupant
x∈[c, c+1], z∈[r, r+1], de centre (c+0,5, r+0,5).

Avec le positionnement actuel, un bâtiment en (row=3, col=7) est rendu à x=7
(limite entre cellules) et son emprise visuelle (±0,425) déborde sur la cellule
libre (3,6). Le drone traversant (3,6) semble ainsi passer à l'intérieur du
bâtiment.

### Fix visuel — `frontend/scene.js`

```js
// Avant
mesh.position.set(b.col * cellSize, h / 2, b.row * cellSize);
// Après
mesh.position.set((b.col + 0.5) * cellSize, h / 2, (b.row + 0.5) * cellSize);
```

Même correction pour les arêtes (`edges.position.copy(mesh.position)`).

### Fix visuel — `frontend/drones.js`

```js
// Avant
_toWorld(pos) {
  return new THREE.Vector3(pos[1] * CELL, ..., pos[0] * CELL);
}
// Après
_toWorld(pos) {
  return new THREE.Vector3((pos[1] + 0.5) * CELL, ..., (pos[0] + 0.5) * CELL);
}
```

Toutes les positions dérivées dans le constructeur (ring, pillar, beacon,
goalRing, star) utilisent `_toWorld` ou les mêmes expressions `pos[1] * CELL` /
`pos[0] * CELL` — toutes sont mises à jour avec le +0,5.

### Fix solveur — horizon insuffisant

Le scénario bottleneck à 6 drones bidirectionnels nécessite que chaque groupe
attende que l'autre libère le tunnel mono-cellule. Le makespan optimal est
≈ 40-50 steps, bien au-dessus de T=28 (CP-SAT) et max_t=35 (CBS) actuels.

**CP-SAT (`solver/mapf.py`)** :
```python
# Avant
T = max(astar_lens) + max(N - 1, 3)
# Après
T = max(astar_lens) + 2 * N + 5
```

**CBS/ECBS (`solver/cbs.py`)** :
```python
# Avant
return (max(valid) if valid else 0) + len(drones) + 5
# Après
return (max(valid) if valid else 0) + 2 * len(drones) + 10
```

---

## Tâche 3 — Optimisations des solveurs

### 3a. CP-SAT — domain reduction (inspiré CSP-4)

**Principe** : pour l'agent a à l'instant t, la position p n'est utile que si :
- `dist_from_start[a][p] <= t` (atteignable depuis le départ)
- `dist_to_goal[a][p] <= T - t` (peut encore atteindre le but)

On calcule deux cartes BFS par agent (réutilisation de `_bfs_dist` déjà dans
`od_astar.py`) et on ne crée les variables `here[a][p][t]` et `move[a,p,q,t]`
que pour les (a, p, t) valides.

Gain attendu : réduction de 50–70 % des variables sur les scénarios denses,
ce qui accélère le build du modèle et le temps de résolution.

**Impact sur le code** : la structure des variables passe de tableaux 3D complets
à des dictionnaires `here: Dict[(a,p,t), BoolVar]` et
`move: Dict[(a,p,q,t), BoolVar]`. Les boucles de contraintes sont adaptées en
conséquence.

### 3b. ECBS — correction de deux bugs de performance (`solver/cbs.py`)

**Bug 1 — f_min en O(N) au lieu de O(1)** :
```python
# Avant
f_min = min(item[0] for item in open_list)
# Après
f_min = open_list[0][0]  # le heap garantit le minimum en tête
```

**Bug 2 — rebuild O(N log N) à chaque itération** :
```python
# Avant
_, chosen_id, node = min(focal, key=lambda x: _count_conflicts(x[2].paths))
open_list = [(c, nid, n) for c, nid, n in open_list if nid != chosen_id]
heapq.heapify(open_list)

# Après — lazy deletion
deleted_ids: set = set()
# ...
_, chosen_id, node = min(focal, key=lambda x: _count_conflicts(x[2].paths))
deleted_ids.add(chosen_id)
# Au moment du pop :
while open_list and open_list[0][1] in deleted_ids:
    heapq.heappop(open_list)
```

---

## Tâche 4 — Timeout CP-SAT (bug 1 ligne)

**Bug** : `solver.parameters.max_time_in_seconds = self.time_limit_s` utilise la
limite complète alors qu'une partie est déjà consommée par le build du modèle.
Sur `full_city_3D` (grille 10×10×3, 8 drones), le build peut prendre 5–8 s,
donnant au total ~18 s pour un timeout de 10 s.

**Fix dans `solver/mapf.py` (ligne ~168)** :
```python
# Avant
solver.parameters.max_time_in_seconds = self.time_limit_s
# Après
solver.parameters.max_time_in_seconds = max(1.0, self.time_limit_s - elapsed_build)
```

---

## Tâche 5 — Réécriture des messages de commit

### Commits à modifier

10 commits consécutifs (du plus récent `195113c` au plus ancien `ecff9c5`)
n'ont pas `(G3)` dans leur scope. Format cible : remplacer le scope existant
par `G3`.

| Commit | Message actuel | Message cible |
|---|---|---|
| 195113c | `fix: restaure timeout CP-SAT + cleanup drones au changement de scène` | `fix(G3): restaure timeout CP-SAT + cleanup drones au changement de scène` |
| 704603d | `feat(frontend): désactive le solve automatique au chargement d'un scénario` | `feat(G3): désactive le solve automatique au chargement d'un scénario` |
| f3ceb12 | `fix: no-cache dev server + CP-SAT timeout includes model build time` | `fix(G3): no-cache dev server + CP-SAT timeout includes model build time` |
| 0bc25f1 | `fix(frontend): use :last-of-type so btn-smooth loses its right border correctly` | `fix(G3): use :last-of-type so btn-smooth loses its right border correctly` |
| 17d9384 | `fix(frontend): smooth mode division guard, lastFrameTime reset, trail update, cache slider ref` | `fix(G3): smooth mode division guard, lastFrameTime reset, trail update, cache slider ref` |
| 400c1dc | `feat(frontend): smooth animation toggle with speed slider` | `feat(G3): smooth animation toggle with speed slider` |
| 7d21c09 | `fix(frontend): timeout input label association, validation guard, step attr` | `fix(G3): timeout input label association, validation guard, step attr` |
| a5e221f | `feat(frontend): configurable timeout input in solver controls` | `feat(G3): configurable timeout input in solver controls` |
| eb2f599 | `fix(frontend): clamp alpha + use lerpVectors in updateFrameLerp` | `fix(G3): clamp alpha + use lerpVectors in updateFrameLerp` |
| ecff9c5 | `feat(frontend): add DroneManager.updateFrameLerp for smooth animation` | `feat(G3): add DroneManager.updateFrameLerp for smooth animation` |

### Approche

Script PowerShell utilisant `git rebase` avec `--exec` pour réécrire les
messages programmatiquement. Nécessite un **`git push --force`** si la branche
`main` est déjà sur le remote EPITA.

---

## Ordre d'implémentation recommandé

1. Tâche 4 (1 ligne, risque zéro)
2. Tâche 1 (suppression propre, pas de logique à casser)
3. Tâche 2 (fix visuel + horizon — touche frontend et solver)
4. Tâche 3 (optimisations solver — changement structurel)
5. Tâche 5 (rewrite git — en dernier pour inclure tous les nouveaux commits)
