# Multi-Method MAPF Solver — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CBS, ECBS, and A* with Operator Decomposition alongside CP-SAT, selectable via a dropdown in the frontend.

**Architecture:** Two new solver files (`solver/cbs.py`, `solver/od_astar.py`) share the existing `Grid`, `Drone`, and `Solution` types. `api/server.py` dispatches to the right solver based on the `method` field. `frontend/index.html` gains a method dropdown and a HUD line for the active method. No changes to `mapf.py`, `grid.py`, or `astar.py`.

**Tech Stack:** Python 3.10+, OR-Tools CP-SAT (existing, unchanged), standard library (heapq, dataclasses), Flask + Flask-CORS (existing), Three.js r128 (existing)

---

## File Map

```
solver/
  cbs.py          [NEW] astar_spacetime, find_first_conflict, CBSSolver, ECBSSolver
  od_astar.py     [NEW] ODAstarSolver

api/
  server.py       [MODIFY] dispatch by method field, pass suboptimality_w

frontend/
  index.html      [MODIFY] add <select id="sel-method">, update HUD, wire fetchSolve

tests/
  test_cbs.py     [NEW]
  test_od_astar.py [NEW]
```

---

## Task 1: Space-Time A* and Conflict Detection

**Files:**
- Create: `solver/cbs.py`
- Create: `tests/test_cbs.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cbs.py
import pytest
from solver.grid import Grid
from solver.cbs import astar_spacetime, find_first_conflict


def test_spacetime_no_constraints():
    g = Grid(rows=4, cols=4)
    path = astar_spacetime(g, (0, 0), (3, 3), set(), max_t=20)
    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (3, 3)
    assert len(path) - 1 == 6  # Manhattan distance (no detour)


def test_spacetime_avoids_constraint():
    g = Grid(rows=4, cols=4)
    # Block (0,1) at t=1 — agent must wait or go around
    path = astar_spacetime(g, (0, 0), (0, 2), {((0, 1), 1)}, max_t=20)
    assert path is not None
    assert path[-1] == (0, 2)
    if len(path) > 1:
        assert path[1] != (0, 1)


def test_find_vertex_conflict():
    paths = {0: [(0, 0), (1, 0), (2, 0)], 1: [(2, 2), (2, 1), (2, 0)]}
    c = find_first_conflict(paths)
    assert c is not None
    assert c[0] == 'vertex'
    assert c[3] == (2, 0)  # position
    assert c[4] == 2       # timestep


def test_find_edge_conflict():
    paths = {0: [(0, 0), (0, 1)], 1: [(0, 1), (0, 0)]}
    c = find_first_conflict(paths)
    assert c is not None
    assert c[0] == 'edge'


def test_no_conflict():
    paths = {0: [(0, 0), (1, 0), (2, 0)], 1: [(3, 3), (3, 2), (3, 1)]}
    assert find_first_conflict(paths) is None
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_cbs.py -v
```
Expected: `ImportError: cannot import name 'astar_spacetime'`

- [ ] **Step 3: Create `solver/cbs.py` with `astar_spacetime` and `find_first_conflict`**

```python
# solver/cbs.py
from __future__ import annotations
import heapq
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from .grid import Grid, Pos
from .mapf import Drone, Solution
from .astar import heuristic

# A vertex constraint: agent must not be at pos at time t
Constraint = Tuple[Pos, int]


def astar_spacetime(
    grid: Grid,
    start: Pos,
    goal: Pos,
    constraints: Set[Constraint],
    max_t: int,
) -> Optional[List[Pos]]:
    """Space-time A* — finds shortest path from start to goal respecting constraints."""
    open_heap: list = []
    heapq.heappush(open_heap, (heuristic(start, goal), 0, start, 0))
    came_from: Dict[Tuple[Pos, int], Optional[Tuple[Pos, int]]] = {(start, 0): None}
    g_score: Dict[Tuple[Pos, int], int] = {(start, 0): 0}

    while open_heap:
        _, g, pos, t = heapq.heappop(open_heap)

        if pos == goal:
            path: List[Pos] = []
            state: Optional[Tuple[Pos, int]] = (pos, t)
            while state is not None:
                path.append(state[0])
                state = came_from.get(state)
            path.reverse()
            return path

        if g > g_score.get((pos, t), float('inf')):
            continue
        if t >= max_t:
            continue

        for nb in grid.neighbors(pos):  # includes wait move (nb == pos)
            nt = t + 1
            if (nb, nt) in constraints:
                continue
            ng = g + 1
            new_state = (nb, nt)
            if ng < g_score.get(new_state, float('inf')):
                g_score[new_state] = ng
                came_from[new_state] = (pos, t)
                heapq.heappush(open_heap, (ng + heuristic(nb, goal), ng, nb, nt))

    return None


def find_first_conflict(paths: Dict[int, List[Pos]]):
    """
    Returns the first conflict found, or None.
    Vertex conflict: ('vertex', agent_a, agent_b, pos, t)
    Edge conflict:   ('edge',   agent_a, agent_b, pos_a, pos_b, t)
    """
    ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())

    for t in range(max_t):
        for i, a in enumerate(ids):
            pa = paths[a][min(t, len(paths[a]) - 1)]
            for b in ids[i + 1:]:
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if pa == pb:
                    return ('vertex', a, b, pa, t)
                if t + 1 < max_t:
                    pa1 = paths[a][min(t + 1, len(paths[a]) - 1)]
                    pb1 = paths[b][min(t + 1, len(paths[b]) - 1)]
                    if pa == pb1 and pb == pa1:
                        return ('edge', a, b, pa, pb, t)
    return None
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_cbs.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```
git add solver/cbs.py tests/test_cbs.py
git commit -m "feat(G3): CBS foundation — space-time A* and conflict detection"
```

---

## Task 2: CBS Solver

**Files:**
- Modify: `solver/cbs.py` (append CBSSolver + helpers)
- Modify: `tests/test_cbs.py` (append CBS tests)

- [ ] **Step 1: Append failing CBS tests to `tests/test_cbs.py`**

```python
# append to tests/test_cbs.py
from solver.mapf import Drone
from solver.cbs import CBSSolver


def test_cbs_single_drone():
    g = Grid(rows=4, cols=4)
    sol = CBSSolver(g, [Drone(0, (0, 0), (3, 3))]).solve()
    assert sol.status == "optimal"
    assert sol.paths[0][-1] == (3, 3)


def test_cbs_two_drones_no_vertex_conflict():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = CBSSolver(g, drones).solve()
    assert sol.status == "optimal"
    max_t = max(len(p) for p in sol.paths.values())
    for t in range(max_t):
        positions = [sol.paths[d.id][min(t, len(sol.paths[d.id]) - 1)] for d in drones]
        assert len(positions) == len(set(positions)), f"Vertex conflict at t={t}"


def test_cbs_all_goals_reached():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0)), Drone(2, (4, 0), (0, 4))]
    sol = CBSSolver(g, drones).solve()
    assert sol.status == "optimal"
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal


def test_cbs_makespan_positive():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = CBSSolver(g, drones).solve()
    assert sol.makespan > 0
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_cbs.py::test_cbs_single_drone -v
```
Expected: `ImportError: cannot import name 'CBSSolver'`

- [ ] **Step 3: Append `_near_passes`, `_CTNode`, and `CBSSolver` to `solver/cbs.py`**

```python
# append to solver/cbs.py

def _near_passes(paths: Dict[int, List[Pos]]) -> int:
    ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    count = 0
    for t in range(max_t):
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pa = paths[a][min(t, len(paths[a]) - 1)]
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if sum(abs(pa[k] - pb[k]) for k in range(len(pa))) == 1:
                    count += 1
    return count


def _count_conflicts(paths: Dict[int, List[Pos]]) -> int:
    """Count total conflicts in paths (used as ECBS tie-breaker)."""
    ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    count = 0
    for t in range(max_t):
        for i, a in enumerate(ids):
            pa = paths[a][min(t, len(paths[a]) - 1)]
            for b in ids[i + 1:]:
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if pa == pb:
                    count += 1
                if t + 1 < max_t:
                    pa1 = paths[a][min(t + 1, len(paths[a]) - 1)]
                    pb1 = paths[b][min(t + 1, len(paths[b]) - 1)]
                    if pa == pb1 and pb == pa1:
                        count += 1
    return count


@dataclass
class _CTNode:
    constraints: Dict[int, Set[Constraint]]
    paths: Dict[int, List[Pos]]
    cost: int  # sum of individual path lengths


def _compute_max_t(grid: Grid, drones: List[Drone]) -> int:
    from .astar import astar
    lens = [len(astar(grid, d.start, d.goal) or [(None,)]) - 1 for d in drones]
    valid = [l for l in lens if l >= 0]
    return (max(valid) if valid else 0) + len(drones) + 5


class CBSSolver:
    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        max_t = _compute_max_t(self.grid, self.drones)
        counter = 0

        root_constraints: Dict[int, Set[Constraint]] = {d.id: set() for d in self.drones}
        root_paths: Dict[int, List[Pos]] = {}
        for drone in self.drones:
            path = astar_spacetime(self.grid, drone.start, drone.goal, set(), max_t)
            if path is None:
                return Solution("infeasible", 0, (time.time() - t0) * 1000, {}, 0)
            root_paths[drone.id] = path

        root = _CTNode(root_constraints, root_paths, sum(len(p) for p in root_paths.values()))
        open_list: list = [(root.cost, counter, root)]
        counter += 1

        while open_list:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, (time.time() - t0) * 1000, {}, 0)

            _, _, node = heapq.heappop(open_list)
            conflict = find_first_conflict(node.paths)

            if conflict is None:
                makespan = max(len(p) for p in node.paths.values()) - 1
                return Solution(
                    status="optimal",
                    makespan=makespan,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=node.paths,
                    conflicts_avoided=_near_passes(node.paths),
                )

            if conflict[0] == 'vertex':
                _, a, b, pos, t = conflict
                new_constraints_list = [(a, (pos, t)), (b, (pos, t))]
            else:
                _, a, b, pos_a, pos_b, t = conflict
                new_constraints_list = [(a, (pos_b, t + 1)), (b, (pos_a, t + 1))]

            for agent_id, new_con in new_constraints_list:
                new_constraints = {d.id: set(node.constraints[d.id]) for d in self.drones}
                new_constraints[agent_id].add(new_con)
                drone = next(d for d in self.drones if d.id == agent_id)
                new_path = astar_spacetime(
                    self.grid, drone.start, drone.goal, new_constraints[agent_id], max_t
                )
                if new_path is None:
                    continue
                new_paths = dict(node.paths)
                new_paths[agent_id] = new_path
                child = _CTNode(new_constraints, new_paths, sum(len(p) for p in new_paths.values()))
                heapq.heappush(open_list, (child.cost, counter, child))
                counter += 1

        return Solution("infeasible", 0, (time.time() - t0) * 1000, {}, 0)
```

- [ ] **Step 4: Run CBS tests**

```
pytest tests/test_cbs.py -v
```
Expected: all 9 tests PASSED

- [ ] **Step 5: Commit**

```
git add solver/cbs.py tests/test_cbs.py
git commit -m "feat(G3): CBSSolver — conflict-based search with space-time A*"
```

---

## Task 3: ECBS Solver

**Files:**
- Modify: `solver/cbs.py` (append ECBSSolver)
- Modify: `tests/test_cbs.py` (append ECBS tests)

- [ ] **Step 1: Append failing ECBS tests**

```python
# append to tests/test_cbs.py
from solver.cbs import ECBSSolver


def test_ecbs_all_goals_reached():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0)), Drone(2, (4, 0), (0, 4))]
    sol = ECBSSolver(g, drones, w=1.3).solve()
    assert sol.status == "feasible"
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal


def test_ecbs_no_vertex_conflict():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = ECBSSolver(g, drones, w=1.3).solve()
    assert sol.status == "feasible"
    max_t = max(len(p) for p in sol.paths.values())
    for t in range(max_t):
        positions = [sol.paths[d.id][min(t, len(sol.paths[d.id]) - 1)] for d in drones]
        assert len(positions) == len(set(positions))
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_cbs.py::test_ecbs_all_goals_reached -v
```
Expected: `ImportError: cannot import name 'ECBSSolver'`

- [ ] **Step 3: Append `ECBSSolver` to `solver/cbs.py`**

```python
# append to solver/cbs.py

class ECBSSolver:
    """
    Enhanced CBS: picks from FOCAL (nodes with cost <= w * f_min) the node with
    fewest conflicts. Guarantees w-suboptimal solution. w=1.0 reduces to CBS.
    """
    def __init__(self, grid: Grid, drones: List[Drone], w: float = 1.3, time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.w = w
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        max_t = _compute_max_t(self.grid, self.drones)
        counter = 0

        root_constraints: Dict[int, Set[Constraint]] = {d.id: set() for d in self.drones}
        root_paths: Dict[int, List[Pos]] = {}
        for drone in self.drones:
            path = astar_spacetime(self.grid, drone.start, drone.goal, set(), max_t)
            if path is None:
                return Solution("infeasible", 0, (time.time() - t0) * 1000, {}, 0)
            root_paths[drone.id] = path

        root = _CTNode(root_constraints, root_paths, sum(len(p) for p in root_paths.values()))
        # open_list entries: (cost, node_id, node)
        open_list: List[Tuple[int, int, _CTNode]] = [(root.cost, counter, root)]
        counter += 1

        while open_list:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, (time.time() - t0) * 1000, {}, 0)

            f_min = min(item[0] for item in open_list)
            focal = [(c, nid, n) for c, nid, n in open_list if c <= self.w * f_min]
            # Pick node with fewest conflicts from focal
            _, chosen_id, node = min(focal, key=lambda x: _count_conflicts(x[2].paths))
            open_list = [(c, nid, n) for c, nid, n in open_list if nid != chosen_id]
            heapq.heapify(open_list)

            conflict = find_first_conflict(node.paths)
            if conflict is None:
                makespan = max(len(p) for p in node.paths.values()) - 1
                return Solution(
                    status="feasible",
                    makespan=makespan,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=node.paths,
                    conflicts_avoided=_near_passes(node.paths),
                )

            if conflict[0] == 'vertex':
                _, a, b, pos, t = conflict
                new_constraints_list = [(a, (pos, t)), (b, (pos, t))]
            else:
                _, a, b, pos_a, pos_b, t = conflict
                new_constraints_list = [(a, (pos_b, t + 1)), (b, (pos_a, t + 1))]

            for agent_id, new_con in new_constraints_list:
                new_constraints = {d.id: set(node.constraints[d.id]) for d in self.drones}
                new_constraints[agent_id].add(new_con)
                drone = next(d for d in self.drones if d.id == agent_id)
                new_path = astar_spacetime(
                    self.grid, drone.start, drone.goal, new_constraints[agent_id], max_t
                )
                if new_path is None:
                    continue
                new_paths = dict(node.paths)
                new_paths[agent_id] = new_path
                child = _CTNode(new_constraints, new_paths, sum(len(p) for p in new_paths.values()))
                heapq.heappush(open_list, (child.cost, counter, child))
                counter += 1

        return Solution("infeasible", 0, (time.time() - t0) * 1000, {}, 0)
```

- [ ] **Step 4: Run all CBS/ECBS tests**

```
pytest tests/test_cbs.py -v
```
Expected: all 11 tests PASSED

- [ ] **Step 5: Commit**

```
git add solver/cbs.py tests/test_cbs.py
git commit -m "feat(G3): ECBSSolver — focal search, w-suboptimal MAPF"
```

---

## Task 4: A* with Operator Decomposition

**Files:**
- Create: `solver/od_astar.py`
- Create: `tests/test_od_astar.py`

Note: OD A* is practical for N ≤ 5. For larger N use CBS/ECBS.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_od_astar.py
import pytest
from solver.grid import Grid
from solver.mapf import Drone
from solver.od_astar import ODAstarSolver


def test_od_single_drone():
    g = Grid(rows=4, cols=4)
    sol = ODAstarSolver(g, [Drone(0, (0, 0), (3, 3))]).solve()
    assert sol.status == "optimal"
    assert sol.paths[0][-1] == (3, 3)


def test_od_two_drones_no_vertex_conflict():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = ODAstarSolver(g, drones).solve()
    assert sol.status == "optimal"
    max_t = max(len(p) for p in sol.paths.values())
    for t in range(max_t):
        positions = [sol.paths[d.id][min(t, len(sol.paths[d.id]) - 1)] for d in drones]
        assert len(positions) == len(set(positions))


def test_od_all_goals_reached():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0))]
    sol = ODAstarSolver(g, drones).solve()
    assert sol.status == "optimal"
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/test_od_astar.py -v
```
Expected: `ModuleNotFoundError: No module named 'solver.od_astar'`

- [ ] **Step 3: Create `solver/od_astar.py`**

```python
# solver/od_astar.py
from __future__ import annotations
import heapq
import time
from typing import Dict, List, Optional, Tuple
from .grid import Grid, Pos
from .mapf import Drone, Solution
from .cbs import _near_passes


def _bfs_dist(grid: Grid, goal: Pos) -> Dict[Pos, int]:
    """BFS from goal (all moves bidirectional) — gives min steps from any pos to goal."""
    dist = {goal: 0}
    queue = [goal]
    while queue:
        nxt = []
        for pos in queue:
            d = dist[pos]
            for nb in grid.neighbors(pos):
                if nb != pos and nb not in dist:
                    dist[nb] = d + 1
                    nxt.append(nb)
        queue = nxt
    return dist


class ODAstarSolver:
    """
    A* with Operator Decomposition for MAPF.

    State: (positions: Tuple[Pos,...], agent_idx: int, t: int)
    - positions[i] is the NEW position for agent i if i < agent_idx,
      the CURRENT (old) position if i >= agent_idx.
    - agent_idx == N means all agents have been assigned their next positions.

    Cost increments by 1 only when transitioning from agent_idx==N to agent_idx==0
    (i.e., one full timestep completed).

    Heuristic: sum of individual BFS distances from each agent's assigned/current
    position to its goal (admissible).
    """

    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        N = len(self.drones)
        starts = tuple(d.start for d in self.drones)
        goals = tuple(d.goal for d in self.drones)
        drone_ids = [d.id for d in self.drones]

        # Precompute BFS distances from each goal
        h_maps = [_bfs_dist(self.grid, goals[i]) for i in range(N)]
        INF = 10 ** 9

        def h(positions: Tuple[Pos, ...]) -> int:
            return sum(h_maps[i].get(positions[i], INF) for i in range(N))

        # State: (positions, prev_positions, agent_idx, t)
        # prev_positions: positions at start of current timestep (for edge-conflict checks)
        init = (starts, starts, 0, 0)
        g_score: Dict = {init: 0}
        came_from: Dict = {init: None}
        counter = 0
        open_heap = [(h(starts), 0, counter, init)]

        while open_heap:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, (time.time() - t0) * 1000, {}, 0)

            _, g, _, state = heapq.heappop(open_heap)
            positions, prev_positions, agent_idx, t = state

            if g > g_score.get(state, INF):
                continue

            # Goal check: standard state (agent_idx==0) with all agents at goals
            if agent_idx == 0 and positions == goals:
                paths = _reconstruct(came_from, state, drone_ids, N)
                makespan = max(len(p) for p in paths.values()) - 1
                return Solution(
                    status="optimal",
                    makespan=makespan,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=paths,
                    conflicts_avoided=_near_passes(paths),
                )

            if agent_idx < N:
                # Assign next position for agent agent_idx
                agent_pos = positions[agent_idx]
                for nb in self.grid.neighbors(agent_pos):
                    # Vertex conflict: nb already assigned to an earlier agent
                    if any(nb == positions[j] for j in range(agent_idx)):
                        continue
                    # Edge conflict (swap) with earlier agents
                    if any(
                        nb == prev_positions[j] and positions[j] == prev_positions[agent_idx]
                        for j in range(agent_idx)
                    ):
                        continue

                    new_pos = list(positions)
                    new_pos[agent_idx] = nb
                    new_positions = tuple(new_pos)
                    new_idx = agent_idx + 1
                    # Cost increases by 1 only on full timestep completion
                    ng = g + (1 if new_idx == N else 0)
                    new_state = (new_positions, prev_positions, new_idx, t)

                    if ng < g_score.get(new_state, INF):
                        g_score[new_state] = ng
                        came_from[new_state] = state
                        counter += 1
                        heapq.heappush(
                            open_heap,
                            (ng + h(new_positions), ng, counter, new_state),
                        )

            else:
                # agent_idx == N: advance timestep
                new_state = (positions, positions, 0, t + 1)
                ng = g
                if ng < g_score.get(new_state, INF):
                    g_score[new_state] = ng
                    came_from[new_state] = state
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (ng + h(positions), ng, counter, new_state),
                    )

        return Solution("infeasible", 0, (time.time() - t0) * 1000, {}, 0)


def _reconstruct(
    came_from: Dict,
    final_state: Tuple,
    drone_ids: List[int],
    N: int,
) -> Dict[int, List[Pos]]:
    """Walk came_from backwards, collect only standard states (agent_idx==0)."""
    standard_positions: List[Tuple[Pos, ...]] = []
    cur = final_state
    while cur is not None:
        positions, _, agent_idx, _ = cur
        if agent_idx == 0:
            standard_positions.append(positions)
        cur = came_from.get(cur)
    standard_positions.reverse()

    paths: Dict[int, List[Pos]] = {did: [] for did in drone_ids}
    for positions in standard_positions:
        for i, did in enumerate(drone_ids):
            paths[did].append(positions[i])
    return paths
```

- [ ] **Step 4: Run OD A* tests**

```
pytest tests/test_od_astar.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```
git add solver/od_astar.py tests/test_od_astar.py
git commit -m "feat(G3): ODAstarSolver — A* with operator decomposition"
```

---

## Task 5: API Dispatch

**Files:**
- Modify: `api/server.py`

- [ ] **Step 1: Read current `api/server.py`** to locate the `/solve` route

The current `/solve` handler ends with:
```python
sol = MAPFSolver(grid, drones, time_limit_s=time_limit).solve()
```

- [ ] **Step 2: Replace that block with dispatch logic**

Replace the imports block at the top of `api/server.py` (keep existing imports, add new ones):

```python
from solver.mapf import Drone, MAPFSolver
from solver.cbs import CBSSolver, ECBSSolver
from solver.od_astar import ODAstarSolver
```

Replace the single `MAPFSolver` call inside `/solve` with:

```python
        method = body.get("method", "cpsat")
        w = float(body.get("suboptimality_w", 1.3))

        if method == "cbs":
            sol = CBSSolver(grid, drones, time_limit_s=time_limit).solve()
        elif method == "ecbs":
            sol = ECBSSolver(grid, drones, w=w, time_limit_s=time_limit).solve()
        elif method == "od_astar":
            sol = ODAstarSolver(grid, drones, time_limit_s=time_limit).solve()
        else:
            sol = MAPFSolver(grid, drones, time_limit_s=time_limit).solve()
```

Also add `"method"` to the JSON response — replace the final `return jsonify(...)` with:

```python
        return jsonify({
            "status": sol.status,
            "method": method,
            "makespan": sol.makespan,
            "solve_time_ms": round(sol.solve_time_ms, 1),
            "conflicts_avoided": sol.conflicts_avoided,
            "paths": {
                str(did): [list(pos) for pos in path]
                for did, path in sol.paths.items()
            },
        })
```

- [ ] **Step 3: Smoke-test each method**

Start the server: `python api/server.py`

Then in another terminal:

```bash
# CBS
curl -s -X POST http://localhost:5050/solve \
  -H "Content-Type: application/json" \
  -d '{"grid":{"rows":4,"cols":4,"alts":1},"drones":[{"id":0,"start":[0,0],"goal":[3,3]},{"id":1,"start":[3,3],"goal":[0,0]}],"nofly":[],"buildings":[],"time_limit_s":10,"method":"cbs"}' \
  | python -m json.tool
```

Expected: `"status": "optimal"`, `"method": "cbs"`, valid paths.

```bash
# ECBS
curl -s -X POST http://localhost:5050/solve \
  -H "Content-Type: application/json" \
  -d '{"grid":{"rows":4,"cols":4,"alts":1},"drones":[{"id":0,"start":[0,0],"goal":[3,3]},{"id":1,"start":[3,3],"goal":[0,0]}],"nofly":[],"buildings":[],"time_limit_s":10,"method":"ecbs","suboptimality_w":1.3}' \
  | python -m json.tool
```

Expected: `"status": "feasible"`, `"method": "ecbs"`.

```bash
# A* OD
curl -s -X POST http://localhost:5050/solve \
  -H "Content-Type: application/json" \
  -d '{"grid":{"rows":4,"cols":4,"alts":1},"drones":[{"id":0,"start":[0,0],"goal":[3,3]},{"id":1,"start":[3,3],"goal":[0,0]}],"nofly":[],"buildings":[],"time_limit_s":10,"method":"od_astar"}' \
  | python -m json.tool
```

Expected: `"status": "optimal"`, `"method": "od_astar"`.

- [ ] **Step 4: Commit**

```
git add api/server.py
git commit -m "feat(G3): API dispatch — method field routes to CBS/ECBS/OD-A*/CP-SAT"
```

---

## Task 6: Frontend Dropdown and HUD

**Files:**
- Modify: `frontend/index.html`

This task has two sub-changes: (a) add the `<select>` in the controls bar, (b) add the method line in the HUD, (c) pass `method` in the fetch call.

- [ ] **Step 1: Read `frontend/index.html`** to find the controls div and HUD div

- [ ] **Step 2: Add method dropdown to the controls bar**

Locate the `<div id="controls">` block. Add the `<select>` element **before** the Solve button:

```html
<select id="sel-method" title="Solving method">
  <option value="cpsat">CP-SAT optimal</option>
  <option value="cbs">CBS (optimal)</option>
  <option value="ecbs">ECBS (rapide ×1.3)</option>
  <option value="od_astar">A* OD (optimal, N≤5)</option>
</select>
```

Add this CSS for the select (inside the existing `<style>` block):

```css
select {
  padding: 8px 12px;
  background: #0f172a;
  border: 1px solid #334155;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
select:hover { border-color: #3b82f6; color: #fff; }
```

- [ ] **Step 3: Add method line to the HUD**

Locate the `<div id="hud">` block. Add a new line (e.g., after the Status line):

```html
<div>Méthode: <span class="val" id="h-method">—</span></div>
```

- [ ] **Step 4: Wire the dropdown to `fetchSolve`**

Locate the `onSolve` handler (or the `btn-solve` click handler) in the `<script type="module">` block.

Before the `fetchSolve` call, read the selected method:

```javascript
const method = document.getElementById('sel-method').value;
```

Pass it in the payload:

```javascript
solution = await fetchSolve({ ...PAYLOAD, nofly, method });
```

After updating the HUD, also set the method:

```javascript
document.getElementById('h-method').textContent = solution.method ?? method;
```

- [ ] **Step 5: Verify in browser**

Start API: `python api/server.py`
Start frontend: `python -m http.server 8080 --directory frontend`
Open: `http://localhost:8080`

Test sequence:
1. Select "CBS (optimal)" → click Solve → HUD shows `Méthode: cbs`
2. Select "ECBS (rapide ×1.3)" → click Solve → HUD shows `Méthode: ecbs`, solve time < CBS
3. Select "CP-SAT optimal" → click Solve for `05_big_city` scenario → note timeout
4. Switch to "ECBS" → Solve → gets result within seconds

- [ ] **Step 6: Commit**

```
git add frontend/index.html
git commit -m "feat(G3): frontend method dropdown + HUD method display"
```

---

## Self-Review

**Spec coverage:**
- ✅ `solver/cbs.py` — CBS (Task 2) + ECBS (Task 3) + foundation helpers (Task 1)
- ✅ `solver/od_astar.py` — A* with OD (Task 4)
- ✅ `api/server.py` — `method` field dispatch + `suboptimality_w` (Task 5)
- ✅ `frontend/index.html` — dropdown + HUD method line (Task 6)
- ✅ All solvers return existing `Solution` type — no frontend parsing changes needed
- ✅ ECBS `status` = `"feasible"` (not `"optimal"`) — confirmed in ECBSSolver.solve()
- ✅ `makespan` for CBS/ECBS computed from paths (`max(len(p)) - 1`) — consistent with spec note

**Type consistency:**
- `astar_spacetime` used by `CBSSolver` and `ECBSSolver` — signature matches in both
- `_compute_max_t` used by both CBS and ECBS — single definition, no duplication
- `_near_passes` defined in `cbs.py`, imported by `od_astar.py` — `from .cbs import _near_passes`
- `_count_conflicts` defined in `cbs.py`, used only by `ECBSSolver` — no cross-file dependency issues
- Frontend reads `solution.method` (returned by API) with `?? method` fallback — safe

**No placeholders found.**
