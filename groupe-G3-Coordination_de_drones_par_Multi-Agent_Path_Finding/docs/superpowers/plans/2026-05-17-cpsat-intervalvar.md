# CP-SAT IntervalVar+NoOverlap Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Réécrire `MAPFSolver.solve()` pour remplacer le modèle BoolVar actuel par `IntervalVar + AddNoOverlap`, réduisant les contraintes d'edge conflict de ~216 000 à ~360 contraintes globales.

**Architecture:** On conserve `here[a][p][t]` (ancien `x`) pour ExactlyOne et l'extraction des chemins. On ajoute `move[a][p][q][t]` pour modéliser les déplacements arc par arc. La conservation de flot (`here` ↔ `move`) remplace les contraintes de mouvement. `AddNoOverlap` par position remplace `AddAtMostOne` par (position, timestep) ; `AddNoOverlap` par arc non orienté remplace les 4-littéraux d'edge conflict. Interface `Solution` inchangée.

**Tech Stack:** Python 3.10+, OR-Tools CP-SAT (`ortools.sat.python.cp_model`), `solver/mapf.py` uniquement.

---

## File Map

```
solver/
  mapf.py     [MODIFY] MAPFSolver.solve() only — Drone, Solution, _near_passes untouched

tests/
  test_mapf.py  [NO CHANGE] existing tests are the correctness spec
```

---

## Task 1 : Vérification baseline

**Files:**
- Read: `tests/test_mapf.py`

- [ ] **Step 1 : Lancer tous les tests existants**

```
.venv\Scripts\python.exe -m pytest tests/test_mapf.py -v
```

Expected: 7 PASSED. Si un test échoue ici, ne pas continuer — corriger d'abord.

---

## Task 2 : Réécriture de MAPFSolver.solve()

**Files:**
- Modify: `solver/mapf.py`

La seule méthode à réécrire est `solve()`. `Drone`, `Solution`, `_near_passes` et `__init__` ne changent pas.

- [ ] **Step 1 : Mettre à jour les imports**

Remplacer la ligne imports `typing` :

```python
from typing import Dict, List, Optional, Set, Tuple
```

- [ ] **Step 2 : Remplacer intégralement `MAPFSolver.solve()`**

Remplacer le corps de `solve()` (lignes 33–161 actuelles) par :

```python
    def solve(self) -> Solution:
        positions = self.grid.positions
        pos_to_idx = {p: i for i, p in enumerate(positions)}
        N = len(self.drones)
        P = len(positions)

        # A* individual paths — horizon + warm-start hints (unchanged)
        astar_paths: List[Optional[List[Pos]]] = [
            astar(self.grid, d.start, d.goal) for d in self.drones
        ]
        astar_lens = [len(p) - 1 for p in astar_paths if p is not None]
        if astar_lens:
            T = max(astar_lens) + max(N - 1, 3)
        else:
            T = 2 * (self.grid.rows + self.grid.cols) + N

        model = cp_model.CpModel()
        t0 = time.time()

        # Neighbor index lists (includes self for wait move)
        nbrs: List[List[int]] = [
            [pos_to_idx[nb] for nb in self.grid.neighbors(positions[p]) if nb in pos_to_idx]
            for p in range(P)
        ]

        # ── Variables ────────────────────────────────────────────────────────
        # here[a][p][t]: agent a is at position p at time t
        here = [
            [[model.NewBoolVar(f'here_{a}_{p}_{t}') for t in range(T + 1)]
             for p in range(P)]
            for a in range(N)
        ]

        # move[(a,p,q,t)]: agent a moves from p to q at time t (q ∈ nbrs[p], includes wait p→p)
        move: Dict[Tuple[int, int, int, int], cp_model.IntVar] = {}
        for a in range(N):
            for t in range(T):
                for p in range(P):
                    for q in nbrs[p]:
                        move[(a, p, q, t)] = model.NewBoolVar(f'mv_{a}_{p}_{q}_{t}')

        # ── Constraints ──────────────────────────────────────────────────────
        # 1. Exactly one position per agent per timestep
        for a in range(N):
            for t in range(T + 1):
                model.AddExactlyOne(here[a][p][t] for p in range(P))

        # 2. Initial positions
        for a, drone in enumerate(self.drones):
            start_idx = pos_to_idx.get(drone.start)
            if start_idx is None:
                return Solution("infeasible", 0, 0, 0.0, {}, 0)
            model.Add(here[a][start_idx][0] == 1)

        # 3. Movement — flow conservation linking here ↔ move
        #    Grid is undirected: nbrs[p] == reverse_nbrs[p] (symmetry + self-loop for wait)
        for a in range(N):
            for t in range(T):
                for p in range(P):
                    # Outgoing: exactly one move leaves p at t iff agent is there
                    model.Add(
                        sum(move[(a, p, q, t)] for q in nbrs[p]) == here[a][p][t]
                    )
                    # Incoming: agent at p at t+1 came from some q via move q→p
                    model.Add(
                        sum(move[(a, q, p, t)] for q in nbrs[p]) == here[a][p][t + 1]
                    )

        # 4. Vertex conflict — AddNoOverlap per position (CSP-4 primitive)
        #    Replaces P*(T+1) individual AddAtMostOne constraints
        for p in range(P):
            model.AddNoOverlap([
                model.NewOptionalIntervalVar(t, 1, t + 1, here[a][p][t], f'ivp_{a}_{p}_{t}')
                for a in range(N)
                for t in range(T + 1)
            ])

        # 5. Edge (swap) conflict — AddNoOverlap per undirected arc (CSP-4 primitive)
        #    Replaces T*N*(N-1)/2*P*avg_nbrs individual 4-literal constraints
        seen_arcs: Set[Tuple[int, int]] = set()
        for p in range(P):
            for q in nbrs[p]:
                if q != p:
                    key = (min(p, q), max(p, q))
                    if key not in seen_arcs:
                        seen_arcs.add(key)
                        iv_arc = []
                        for a in range(N):
                            for t in range(T):
                                iv_arc.append(model.NewOptionalIntervalVar(
                                    t, 1, t + 1, move[(a, p, q, t)], f'iva_{a}_{p}_{q}_{t}'
                                ))
                                iv_arc.append(model.NewOptionalIntervalVar(
                                    t, 1, t + 1, move[(a, q, p, t)], f'iva_{a}_{q}_{p}_{t}'
                                ))
                        model.AddNoOverlap(iv_arc)

        # 6. Goal persistence: once at goal, stay there
        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx.get(drone.goal)
            if goal_idx is None:
                return Solution("infeasible", 0, 0, 0.0, {}, 0)
            for t in range(T):
                model.Add(here[a][goal_idx][t + 1] >= here[a][goal_idx][t])

        # ── Objective (unchanged) ─────────────────────────────────────────────
        makespan_var = model.NewIntVar(0, T, 'makespan')
        arrival_vars = []
        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx[drone.goal]
            arr = model.NewIntVar(0, T, f'arrival_{a}')
            model.Add(arr == T + 1 - sum(here[a][goal_idx][t] for t in range(T + 1)))
            arrival_vars.append(arr)
        model.AddMaxEquality(makespan_var, arrival_vars)
        model.Minimize(makespan_var)

        # ── Warm-start (unchanged, on here instead of x) ─────────────────────
        for a, path in enumerate(astar_paths):
            if path is None:
                continue
            for t in range(T + 1):
                pos = path[min(t, len(path) - 1)]
                hint_idx = pos_to_idx.get(pos)
                if hint_idx is None:
                    continue
                for p in range(P):
                    model.AddHint(here[a][p][t], 1 if p == hint_idx else 0)

        # ── Solve ─────────────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_s
        solver.parameters.num_search_workers = 4

        status_code = solver.Solve(model)
        solve_time_ms = (time.time() - t0) * 1000

        status_map = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.UNKNOWN: "timeout",
            cp_model.MODEL_INVALID: "infeasible",
        }

        if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return Solution(status_map.get(status_code, "unknown"), 0, 0, solve_time_ms, {}, 0)

        makespan_val = int(solver.ObjectiveValue())

        # ── Path extraction (unchanged, here instead of x) ───────────────────
        paths: Dict[int, List[Pos]] = {}
        for a, drone in enumerate(self.drones):
            path: List[Pos] = []
            for t in range(makespan_val + 1):
                for p in range(P):
                    if solver.Value(here[a][p][t]):
                        path.append(positions[p])
                        break
            paths[drone.id] = path

        flowtime = sum(int(solver.Value(arr)) for arr in arrival_vars)
        return Solution(
            status=status_map.get(status_code, "unknown"),
            makespan=makespan_val,
            flowtime=flowtime,
            solve_time_ms=solve_time_ms,
            paths=paths,
            conflicts_avoided=self._near_passes(paths),
        )
```

- [ ] **Step 3 : Commit**

```bash
git add solver/mapf.py
git commit -m "perf(G3): CP-SAT — IntervalVar+NoOverlap remplace BoolVar+4-littéraux"
```

---

## Task 3 : Vérification correctness

**Files:**
- Read: `tests/test_mapf.py`, `tests/test_api.py`

- [ ] **Step 1 : Lancer la suite complète**

```
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **37 PASSED**. Si un test échoue, investiguer avant de continuer.

- [ ] **Step 2 : Benchmark manuel — medium city**

Lancer l'API et chronométrer le scénario `04_medium_city` (8×6×3, 6 drones) avec méthode CP-SAT :

```bash
# Terminal 1
.venv\Scripts\python.exe -m flask --app api.server run --port 5050

# Terminal 2
curl -s -X POST http://localhost:5050/solve \
  -H "Content-Type: application/json" \
  -d @scenarios/04_medium_city.json | python -m json.tool
```

Ou via l'UI : charger le scénario `medium_city`, sélectionner CP-SAT, cliquer Solve.

Expected : `solve_time_ms` nettement inférieur à la valeur baseline (~16 000 ms).

- [ ] **Step 3 : Commit final si benchmark satisfaisant**

```bash
git add .
git commit -m "test(G3): vérification CP-SAT IntervalVar — tous tests passent"
```

---

## Self-Review

**Spec coverage :**
- ✅ `here[a][p][t]` = `IntervalVar` optionnel par position → `AddNoOverlap` par position (section 4 spec)
- ✅ `move[a][p][q][t]` = `IntervalVar` optionnel par arc → `AddNoOverlap` par arc non orienté (section 5 spec)
- ✅ Conservation de flot (outgoing + incoming) remplace l'ancienne contrainte de mouvement (section 3 spec)
- ✅ Interface `Solution` inchangée — tous les tests existants couvrent la correctness
- ✅ Warm-start, horizon, objectif, extraction des chemins : inchangés
- ✅ Un seul fichier modifié : `solver/mapf.py`

**Placeholder scan :** aucun TBD, aucun "similar to above", code complet dans chaque step.

**Type consistency :**
- `move[(a, p, q, t)]` créé dans Task 2 Step 2 et utilisé dans les contraintes 3, 5 du même step ✓
- `here[a][p][t]` remplace `x[a][p][t]` partout dans solve() ✓
- `Solution("infeasible", 0, 0, 0.0, {}, 0)` : 6 args, correspond au dataclass `(status, makespan, flowtime, solve_time_ms, paths, conflicts_avoided)` ✓
