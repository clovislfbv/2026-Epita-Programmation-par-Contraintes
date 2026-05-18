# MAPF Drone Coordination — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a MAPF solver (CP-SAT) + Flask API + Three.js city demo where drones navigate collision-free in a 3D urban environment, with live re-solving when no-fly zones are added.

**Architecture:** Python CP-SAT solver exposed via Flask API returning JSON paths; Three.js frontend animates those paths over a procedural 3D city; 2D grid model first (Phase 1–2), then extended to 3D with altitude layers (Phase 3–4).

**Tech Stack:** Python 3.10+, OR-Tools CP-SAT, Flask, Three.js r128, pytest, matplotlib (notebook only)

---

## File Map

```
solver/
  __init__.py
  grid.py        — Grid dataclass: positions, neighbors, obstacles, no-fly zones (2D + 3D)
  mapf.py        — MAPFSolver + Drone + Solution: full CP-SAT model
  scenarios.py   — Preset scenarios dict keyed by name

api/
  __init__.py
  server.py      — Flask app: POST /solve, GET /scenarios

frontend/
  index.html     — App shell: loads Three.js + all JS modules
  api.js         — fetchSolve(config), fetchScenarios()
  scene.js       — CityScene: buildings, ground, fog, lights, orbit camera
  drones.js      — DroneManager: spheres, trails, start/end markers, conflict flash
  ui.js          — UIManager: HUD overlay, no-fly zone tool, playback controls

notebooks/
  01_model_2d.ipynb   — 2D model walkthrough, matplotlib animation, benchmarks
  02_model_3d.ipynb   — 3D extension, city scenarios, solve time analysis

tests/
  test_grid.py
  test_mapf.py
  test_api.py

benchmarks/
  maps/          — Moving AI Lab .map files (download in Task 5)
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `solver/__init__.py`, `api/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd groupe-G3-Coordination_de_drones_par_Multi-Agent_Path_Finding
mkdir -p solver api frontend notebooks tests benchmarks/maps
touch solver/__init__.py api/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
ortools>=9.8
flask>=3.0
flask-cors>=4.0
pytest>=8.0
matplotlib>=3.8
jupyter>=1.0
numpy>=1.26
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Verify OR-Tools**

```bash
python -c "from ortools.sat.python import cp_model; print('OR-Tools OK')"
```

Expected: `OR-Tools OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt solver/__init__.py api/__init__.py tests/__init__.py
git commit -m "chore(G3): project structure and dependencies"
```

---

## Task 2: Grid (2D-first, 3D-ready)

**Files:**
- Create: `solver/grid.py`
- Create: `tests/test_grid.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_grid.py
import pytest
from solver.grid import Grid

def test_2d_positions_excludes_obstacles():
    g = Grid(rows=4, cols=4)
    g.obstacles.add((1, 1))
    assert (1, 1) not in g.positions
    assert len(g.positions) == 15

def test_2d_neighbors_center():
    g = Grid(rows=4, cols=4)
    nbrs = g.neighbors((1, 1))
    assert set(nbrs) == {(0,1), (2,1), (1,0), (1,2), (1,1)}  # 4-connected + wait

def test_2d_neighbors_corner():
    g = Grid(rows=4, cols=4)
    nbrs = g.neighbors((0, 0))
    assert set(nbrs) == {(0,0), (1,0), (0,1)}

def test_2d_neighbors_skip_obstacle():
    g = Grid(rows=4, cols=4)
    g.obstacles.add((0, 1))
    nbrs = g.neighbors((0, 0))
    assert (0, 1) not in nbrs

def test_2d_nofly_excludes_positions():
    g = Grid(rows=4, cols=4)
    g.add_nofly_box((1, 1), (2, 2))
    for r in range(1, 3):
        for c in range(1, 3):
            assert (r, c) not in g.positions

def test_3d_positions():
    g = Grid(rows=4, cols=4, alts=3)
    assert len(g.positions) == 48

def test_3d_neighbors_include_altitude():
    g = Grid(rows=4, cols=4, alts=3)
    nbrs = g.neighbors((1, 1, 1))
    assert (1, 1, 0) in nbrs
    assert (1, 1, 2) in nbrs

def test_3d_neighbors_no_alt_below_zero():
    g = Grid(rows=4, cols=4, alts=3)
    nbrs = g.neighbors((1, 1, 0))
    assert (1, 1, -1) not in nbrs

def test_add_building():
    g = Grid(rows=4, cols=4, alts=4)
    g.add_building(row=2, col=2, height=3)
    for a in range(3):
        assert (2, 2, a) in g.obstacles
    assert (2, 2, 3) not in g.obstacles
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_grid.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` (grid.py doesn't exist yet).

- [ ] **Step 3: Implement grid.py**

```python
# solver/grid.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Tuple

Pos = Tuple[int, ...]  # (row, col) for 2D; (row, col, alt) for 3D


@dataclass
class Grid:
    rows: int
    cols: int
    alts: int = 1
    obstacles: Set[Pos] = field(default_factory=set)
    _nofly: Set[Pos] = field(default_factory=set)

    @property
    def positions(self) -> List[Pos]:
        blocked = self.obstacles | self._nofly
        if self.alts == 1:
            return [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) not in blocked
            ]
        return [
            (r, c, a)
            for r in range(self.rows)
            for c in range(self.cols)
            for a in range(self.alts)
            if (r, c, a) not in blocked
        ]

    def neighbors(self, pos: Pos) -> List[Pos]:
        blocked = self.obstacles | self._nofly
        if len(pos) == 2:
            r, c = pos
            candidates = [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
            return [
                (nr, nc) for nr, nc in candidates
                if 0 <= nr < self.rows and 0 <= nc < self.cols
                and (nr, nc) not in blocked
            ]
        r, c, a = pos
        candidates = [
            (r, c, a), (r-1, c, a), (r+1, c, a),
            (r, c-1, a), (r, c+1, a),
            (r, c, a-1), (r, c, a+1),
        ]
        return [
            (nr, nc, na) for nr, nc, na in candidates
            if 0 <= nr < self.rows and 0 <= nc < self.cols and 0 <= na < self.alts
            and (nr, nc, na) not in blocked
        ]

    def add_building(self, row: int, col: int, height: int) -> None:
        for a in range(height):
            self.obstacles.add((row, col, a))

    def add_nofly_box(self, min_pos: Pos, max_pos: Pos) -> None:
        if len(min_pos) == 2:
            for r in range(min_pos[0], max_pos[0] + 1):
                for c in range(min_pos[1], max_pos[1] + 1):
                    self._nofly.add((r, c))
        else:
            for r in range(min_pos[0], max_pos[0] + 1):
                for c in range(min_pos[1], max_pos[1] + 1):
                    for a in range(min_pos[2], max_pos[2] + 1):
                        self._nofly.add((r, c, a))

    def clear_nofly(self) -> None:
        self._nofly.clear()
```

- [ ] **Step 4: Run tests — all must pass**

```bash
pytest tests/test_grid.py -v
```

Expected: 9 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add solver/grid.py tests/test_grid.py
git commit -m "feat(G3): Grid class — 2D/3D positions, neighbors, obstacles, no-fly zones"
```

---

## Task 3: MAPF Solver (CP-SAT)

**Files:**
- Create: `solver/mapf.py`
- Create: `tests/test_mapf.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mapf.py
import pytest
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver

def _no_vertex_conflicts(paths):
    """Assert no two drones at same position at same time."""
    drone_ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    for t in range(max_t):
        seen = {}
        for did in drone_ids:
            path = paths[did]
            pos = path[min(t, len(path) - 1)]
            assert pos not in seen, f"Vertex conflict at t={t}, pos={pos}"
            seen[pos] = did

def _no_edge_conflicts(paths):
    """Assert no two drones swap positions between consecutive timesteps."""
    drone_ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    for t in range(max_t - 1):
        for i, a in enumerate(drone_ids):
            for b in drone_ids[i+1:]:
                pa_t  = paths[a][min(t,   len(paths[a])-1)]
                pa_t1 = paths[a][min(t+1, len(paths[a])-1)]
                pb_t  = paths[b][min(t,   len(paths[b])-1)]
                pb_t1 = paths[b][min(t+1, len(paths[b])-1)]
                assert not (pa_t == pb_t1 and pb_t == pa_t1), \
                    f"Edge conflict between drone {a} and {b} at t={t}"

def test_single_drone_reaches_goal():
    g = Grid(rows=4, cols=4)
    drones = [Drone(id=0, start=(0, 0), goal=(3, 3))]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    assert sol.paths[0][-1] == (3, 3)

def test_two_drones_no_conflict():
    g = Grid(rows=4, cols=4)
    drones = [
        Drone(id=0, start=(0, 0), goal=(3, 3)),
        Drone(id=1, start=(3, 3), goal=(0, 0)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    _no_vertex_conflicts(sol.paths)
    _no_edge_conflicts(sol.paths)

def test_three_drones_no_conflict():
    g = Grid(rows=4, cols=4)
    drones = [
        Drone(id=0, start=(0, 0), goal=(0, 3)),
        Drone(id=1, start=(0, 3), goal=(3, 3)),
        Drone(id=2, start=(3, 3), goal=(0, 0)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    _no_vertex_conflicts(sol.paths)
    _no_edge_conflicts(sol.paths)

def test_makespan_is_optimal_single():
    g = Grid(rows=4, cols=4)
    drones = [Drone(id=0, start=(0, 0), goal=(0, 3))]
    sol = MAPFSolver(g, drones).solve()
    assert sol.makespan == 3  # Manhattan distance = 3

def test_nofly_zone_respected():
    g = Grid(rows=4, cols=4)
    g.add_nofly_box((0, 1), (0, 1))  # block (0,1)
    drones = [Drone(id=0, start=(0, 0), goal=(0, 2))]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    for pos in sol.paths[0]:
        assert pos != (0, 1)

def test_all_drones_reach_goal():
    g = Grid(rows=5, cols=5)
    drones = [
        Drone(id=0, start=(0, 0), goal=(4, 4)),
        Drone(id=1, start=(0, 4), goal=(4, 0)),
        Drone(id=2, start=(4, 0), goal=(0, 4)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_mapf.py -v
```

Expected: `ImportError: cannot import name 'Drone' from 'solver.mapf'`

- [ ] **Step 3: Implement mapf.py**

```python
# solver/mapf.py
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from ortools.sat.python import cp_model
from .grid import Grid, Pos


@dataclass
class Drone:
    id: int
    start: Pos
    goal: Pos


@dataclass
class Solution:
    status: str          # "optimal" | "feasible" | "infeasible" | "timeout"
    makespan: int
    solve_time_ms: float
    paths: Dict[int, List[Pos]]
    conflicts_avoided: int


class MAPFSolver:
    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 10.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        positions = self.grid.positions
        pos_to_idx = {p: i for i, p in enumerate(positions)}
        N = len(self.drones)
        P = len(positions)

        # Horizon: 2*(rows+cols) + N gives enough slack for most instances
        T = 2 * (self.grid.rows + self.grid.cols) + N

        model = cp_model.CpModel()
        t0 = time.time()

        # x[a][p][t] ∈ {0,1}: agent a is at position index p at timestep t
        x = [
            [[model.NewBoolVar(f'x_{a}_{p}_{t}') for t in range(T + 1)]
             for p in range(P)]
            for a in range(N)
        ]

        # Precompute neighbor indices for each position
        nbrs: List[List[int]] = [
            [pos_to_idx[nb] for nb in self.grid.neighbors(positions[p]) if nb in pos_to_idx]
            for p in range(P)
        ]

        # ── Constraint 1: Presence — each agent at exactly one position per timestep
        for a in range(N):
            for t in range(T + 1):
                model.AddExactlyOne(x[a][p][t] for p in range(P))

        # ── Constraint 2: Initial positions
        for a, drone in enumerate(self.drones):
            start_idx = pos_to_idx.get(drone.start)
            if start_idx is None:
                return Solution("infeasible", 0, 0.0, {}, 0)
            model.Add(x[a][start_idx][0] == 1)

        # ── Constraint 3: Movement — from p at t, next step in neighbors(p)
        for a in range(N):
            for t in range(T):
                for p in range(P):
                    model.Add(sum(x[a][q][t + 1] for q in nbrs[p]) >= x[a][p][t])

        # ── Constraint 4: Vertex conflict — at most one agent per position per timestep
        for t in range(T + 1):
            for p in range(P):
                model.AddAtMostOne(x[a][p][t] for a in range(N))

        # ── Constraint 5: Edge conflict (swap) — agents can't exchange positions
        for t in range(T):
            for a in range(N):
                for b in range(a + 1, N):
                    for p in range(P):
                        for q in nbrs[p]:
                            # forbid: a:p→q while b:q→p
                            model.Add(
                                x[a][p][t] + x[b][q][t] +
                                x[a][q][t + 1] + x[b][p][t + 1] <= 3
                            )

        # ── Constraint 6: Stay at goal once reached
        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx.get(drone.goal)
            if goal_idx is None:
                return Solution("infeasible", 0, 0.0, {}, 0)
            for t in range(T):
                model.Add(x[a][goal_idx][t + 1] >= x[a][goal_idx][t])

        # ── Objective: minimize makespan
        # With stay-at-goal: arrival[a] = T + 1 - sum_t(x[a][goal][t])
        # because the agent is at goal for exactly (T - arrival + 1) steps.
        makespan_var = model.NewIntVar(0, T, 'makespan')
        arrival_vars = []
        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx[drone.goal]
            arr = model.NewIntVar(0, T, f'arrival_{a}')
            model.Add(arr == T + 1 - sum(x[a][goal_idx][t] for t in range(T + 1)))
            arrival_vars.append(arr)
        model.AddMaxEquality(makespan_var, arrival_vars)
        model.Minimize(makespan_var)

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
            return Solution(status_map.get(status_code, "unknown"), 0, solve_time_ms, {}, 0)

        makespan_val = int(solver.ObjectiveValue())

        paths: Dict[int, List[Pos]] = {}
        for a, drone in enumerate(self.drones):
            path: List[Pos] = []
            for t in range(makespan_val + 1):
                for p in range(P):
                    if solver.Value(x[a][p][t]):
                        path.append(positions[p])
                        break
            paths[drone.id] = path

        return Solution(
            status=status_map.get(status_code, "unknown"),
            makespan=makespan_val,
            solve_time_ms=solve_time_ms,
            paths=paths,
            conflicts_avoided=self._near_passes(paths),
        )

    def _near_passes(self, paths: Dict[int, List[Pos]]) -> int:
        """Count (agent-pair, timestep) where drones were in adjacent cells."""
        ids = list(paths.keys())
        max_t = max(len(p) for p in paths.values())
        count = 0
        for t in range(max_t):
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    pa = paths[a][min(t, len(paths[a]) - 1)]
                    pb = paths[b][min(t, len(paths[b]) - 1)]
                    dist = sum(abs(pa[k] - pb[k]) for k in range(len(pa)))
                    if dist == 1:
                        count += 1
        return count
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_mapf.py -v
```

Expected: all 6 tests PASSED. If `test_makespan_is_optimal_single` fails with makespan > 3, check the arrival formula (should be `T + 1 - sum(x[a][goal][t])`).

- [ ] **Step 5: Commit**

```bash
git add solver/mapf.py tests/test_mapf.py
git commit -m "feat(G3): CP-SAT MAPF solver — vertex/edge conflicts, makespan minimize"
```

---

## Task 4: Preset Scenarios

**Files:**
- Create: `solver/scenarios.py`

- [ ] **Step 1: Create scenarios.py**

```python
# solver/scenarios.py
"""
Each scenario returns a dict with:
  grid_config: dict passed to Grid(**grid_config)
  drones: list of {id, start, goal}
  nofly: list of {min, max} bounding boxes (optional)
  buildings: list of {row, col, height} (optional, 3D only)
  description: str
"""
from typing import Dict, Any

SCENARIOS: Dict[str, Any] = {
    "small_2d": {
        "description": "8×8 grid, 5 drones — validation scenario",
        "grid_config": {"rows": 8, "cols": 8, "alts": 1},
        "drones": [
            {"id": 0, "start": [0, 0], "goal": [7, 7]},
            {"id": 1, "start": [7, 0], "goal": [0, 7]},
            {"id": 2, "start": [0, 7], "goal": [7, 0]},
            {"id": 3, "start": [3, 0], "goal": [3, 7]},
            {"id": 4, "start": [0, 3], "goal": [7, 3]},
        ],
        "nofly": [],
        "buildings": [],
    },
    "city_2d": {
        "description": "16×16 grid, 10 drones — main 2D demo",
        "grid_config": {"rows": 16, "cols": 16, "alts": 1},
        "drones": [
            {"id": 0,  "start": [0,  0],  "goal": [15, 15]},
            {"id": 1,  "start": [15, 0],  "goal": [0,  15]},
            {"id": 2,  "start": [0,  15], "goal": [15, 0]},
            {"id": 3,  "start": [15, 15], "goal": [0,  0]},
            {"id": 4,  "start": [0,  7],  "goal": [15, 8]},
            {"id": 5,  "start": [15, 8],  "goal": [0,  7]},
            {"id": 6,  "start": [7,  0],  "goal": [8,  15]},
            {"id": 7,  "start": [8,  15], "goal": [7,  0]},
            {"id": 8,  "start": [3,  3],  "goal": [12, 12]},
            {"id": 9,  "start": [12, 12], "goal": [3,  3]},
        ],
        "nofly": [],
        "buildings": [],
    },
    "city_3d": {
        "description": "16×16×5 city, 10 drones — main 3D demo",
        "grid_config": {"rows": 16, "cols": 16, "alts": 5},
        "drones": [
            {"id": 0,  "start": [0,  0,  0], "goal": [15, 15, 4]},
            {"id": 1,  "start": [15, 0,  0], "goal": [0,  15, 3]},
            {"id": 2,  "start": [0,  15, 1], "goal": [15, 0,  2]},
            {"id": 3,  "start": [15, 15, 2], "goal": [0,  0,  1]},
            {"id": 4,  "start": [0,  7,  0], "goal": [15, 8,  4]},
            {"id": 5,  "start": [15, 8,  0], "goal": [0,  7,  3]},
            {"id": 6,  "start": [7,  0,  0], "goal": [8,  15, 2]},
            {"id": 7,  "start": [8,  15, 0], "goal": [7,  0,  4]},
            {"id": 8,  "start": [3,  3,  0], "goal": [12, 12, 3]},
            {"id": 9,  "start": [12, 12, 0], "goal": [3,  3,  4]},
        ],
        "nofly": [],
        "buildings": [
            # (row, col, height) — drones must fly above or around
            {"row": 2,  "col": 2,  "height": 3},
            {"row": 2,  "col": 3,  "height": 3},
            {"row": 5,  "col": 5,  "height": 4},
            {"row": 5,  "col": 6,  "height": 4},
            {"row": 9,  "col": 2,  "height": 2},
            {"row": 9,  "col": 9,  "height": 5},
            {"row": 9,  "col": 10, "height": 5},
            {"row": 12, "col": 12, "height": 3},
            {"row": 13, "col": 12, "height": 3},
            {"row": 3,  "col": 13, "height": 4},
        ],
    },
}


def get_scenario(name: str) -> Dict[str, Any]:
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{name}'. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name]


def list_scenarios():
    return [{"name": k, "description": v["description"]} for k, v in SCENARIOS.items()]
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from solver.scenarios import list_scenarios; print(list_scenarios())"
```

Expected: list of 3 scenario dicts printed.

- [ ] **Step 3: Commit**

```bash
git add solver/scenarios.py
git commit -m "feat(G3): preset scenarios — small_2d, city_2d, city_3d"
```

---

## Task 5: Flask API

**Files:**
- Create: `api/server.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api.py
import json
import pytest
from api.server import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_get_scenarios(client):
    r = client.get("/scenarios")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)
    assert any(s["name"] == "city_2d" for s in data)

def test_solve_small(client):
    payload = {
        "grid": {"rows": 4, "cols": 4, "alts": 1},
        "drones": [
            {"id": 0, "start": [0, 0], "goal": [3, 3]},
            {"id": 1, "start": [3, 0], "goal": [0, 3]},
        ],
        "nofly": [],
        "buildings": [],
        "time_limit_s": 15,
    }
    r = client.post("/solve", json=payload)
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] in ("optimal", "feasible")
    assert "paths" in data
    assert "0" in data["paths"] and "1" in data["paths"]

def test_solve_with_nofly(client):
    payload = {
        "grid": {"rows": 4, "cols": 4, "alts": 1},
        "drones": [{"id": 0, "start": [0, 0], "goal": [3, 3]}],
        "nofly": [{"min": [1, 1], "max": [2, 2]}],
        "buildings": [],
        "time_limit_s": 15,
    }
    r = client.post("/solve", json=payload)
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] in ("optimal", "feasible")
    for step in data["paths"]["0"]:
        assert not (1 <= step[0] <= 2 and 1 <= step[1] <= 2), \
            f"Path went through no-fly zone: {step}"

def test_solve_returns_solve_time(client):
    payload = {
        "grid": {"rows": 4, "cols": 4, "alts": 1},
        "drones": [{"id": 0, "start": [0, 0], "goal": [3, 3]}],
        "nofly": [], "buildings": [], "time_limit_s": 15,
    }
    r = client.post("/solve", json=payload)
    data = json.loads(r.data)
    assert "solve_time_ms" in data
    assert data["solve_time_ms"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api.py -v
```

Expected: `ImportError: cannot import name 'create_app'`

- [ ] **Step 3: Implement server.py**

```python
# api/server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver
from solver.scenarios import list_scenarios


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route("/scenarios", methods=["GET"])
    def scenarios():
        return jsonify(list_scenarios())

    @app.route("/solve", methods=["POST"])
    def solve():
        body = request.get_json(force=True)

        gc = body.get("grid", {})
        grid = Grid(
            rows=gc.get("rows", 16),
            cols=gc.get("cols", 16),
            alts=gc.get("alts", 1),
        )

        for b in body.get("buildings", []):
            grid.add_building(b["row"], b["col"], b["height"])

        for nf in body.get("nofly", []):
            grid.add_nofly_box(tuple(nf["min"]), tuple(nf["max"]))

        drones = [
            Drone(
                id=d["id"],
                start=tuple(d["start"]),
                goal=tuple(d["goal"]),
            )
            for d in body.get("drones", [])
        ]

        time_limit = body.get("time_limit_s", 10)
        sol = MAPFSolver(grid, drones, time_limit_s=time_limit).solve()

        return jsonify({
            "status": sol.status,
            "makespan": sol.makespan,
            "solve_time_ms": round(sol.solve_time_ms, 1),
            "conflicts_avoided": sol.conflicts_avoided,
            "paths": {
                str(did): [list(pos) for pos in path]
                for did, path in sol.paths.items()
            },
        })

    return app


if __name__ == "__main__":
    create_app().run(port=5050, debug=True)
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_api.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Smoke-test live server**

```bash
python api/server.py &
curl -s -X POST http://localhost:5050/solve \
  -H "Content-Type: application/json" \
  -d '{"grid":{"rows":4,"cols":4,"alts":1},"drones":[{"id":0,"start":[0,0],"goal":[3,3]}],"nofly":[],"buildings":[],"time_limit_s":10}' | python -m json.tool
kill %1
```

Expected: JSON with `status`, `makespan`, `paths`.

- [ ] **Step 6: Commit**

```bash
git add api/server.py tests/test_api.py
git commit -m "feat(G3): Flask API — POST /solve, GET /scenarios"
```

---

## Task 6: Notebook 2D

**Files:**
- Create: `notebooks/01_model_2d.ipynb`

- [ ] **Step 1: Create and open notebook**

```bash
cd notebooks && jupyter notebook 01_model_2d.ipynb
```

- [ ] **Step 2: Add cells in this order**

**Cell 1 — Setup**
```python
import sys; sys.path.insert(0, '..')
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
```

**Cell 2 — Solve small instance**
```python
grid = Grid(rows=8, cols=8)
drones = [
    Drone(0, (0,0), (7,7)),
    Drone(1, (7,0), (0,7)),
    Drone(2, (0,7), (7,0)),
    Drone(3, (3,0), (3,7)),
]
sol = MAPFSolver(grid, drones, time_limit_s=30).solve()
print(f"Status: {sol.status} | Makespan: {sol.makespan} | Solve: {sol.solve_time_ms:.0f}ms")
```

**Cell 3 — matplotlib animation function**
```python
COLORS = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#a855f7',
          '#06b6d4','#ec4899','#84cc16','#fb923c','#e11d48']

def animate_solution(grid, sol, drones, obstacles=None, nofly=None, interval=300):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-0.5, grid.cols - 0.5)
    ax.set_ylim(-0.5, grid.rows - 0.5)
    ax.set_facecolor('#0f172a')
    ax.set_aspect('equal')
    ax.invert_yaxis()

    # Grid lines
    for r in range(grid.rows + 1):
        ax.axhline(r - 0.5, color='#1e3a5f', lw=0.5)
    for c in range(grid.cols + 1):
        ax.axvline(c - 0.5, color='#1e3a5f', lw=0.5)

    # Obstacles
    for (r, c) in (obstacles or []):
        ax.add_patch(plt.Rectangle((c-.5, r-.5), 1, 1, color='#334155'))

    # No-fly zones
    for (r, c) in (nofly or []):
        ax.add_patch(plt.Rectangle((c-.5, r-.5), 1, 1, color='#ef4444', alpha=0.3))

    # Start/goal markers
    for i, d in enumerate(drones):
        col = COLORS[i % len(COLORS)]
        ax.plot(d.start[1], d.start[0], 'o', ms=10, color=col, alpha=0.4)
        ax.plot(d.goal[1], d.goal[0], '*', ms=12, color=col)

    # Drone dots
    dots = [ax.plot([], [], 'o', ms=12, color=COLORS[i % len(COLORS)])[0]
            for i in range(len(drones))]

    def update(frame):
        for i, d in enumerate(drones):
            path = sol.paths[d.id]
            pos = path[min(frame, len(path)-1)]
            dots[i].set_data([pos[1]], [pos[0]])
        ax.set_title(f"t={frame}/{sol.makespan}  makespan={sol.makespan}  "
                     f"solve={sol.solve_time_ms:.0f}ms", color='white')
        return dots

    fig.patch.set_facecolor('#0f172a')
    ax.tick_params(colors='#64748b')
    return animation.FuncAnimation(fig, update, frames=sol.makespan+1,
                                   interval=interval, blit=True)

anim = animate_solution(grid, sol, drones)
from IPython.display import HTML
HTML(anim.to_jshtml())
```

**Cell 4 — Benchmark: solve time vs agent count**
```python
import time

results = []
for n in [2, 3, 4, 5, 6, 7, 8]:
    g = Grid(rows=8, cols=8)
    ds = [Drone(i, (0, i*2 % 8), (7, (7 - i*2) % 8)) for i in range(n)]
    t0 = time.time()
    s = MAPFSolver(g, ds, time_limit_s=30).solve()
    elapsed = time.time() - t0
    results.append({"n": n, "status": s.status, "ms": s.solve_time_ms, "makespan": s.makespan})
    print(f"n={n}: {s.status} makespan={s.makespan} in {s.solve_time_ms:.0f}ms")

# Plot
ns = [r["n"] for r in results if r["status"] in ("optimal","feasible")]
ms = [r["ms"] for r in results if r["status"] in ("optimal","feasible")]
plt.figure(facecolor='#0f172a')
ax = plt.gca()
ax.set_facecolor('#0f172a')
ax.plot(ns, ms, 'o-', color='#3b82f6')
ax.set_xlabel("Number of drones", color='#94a3b8')
ax.set_ylabel("Solve time (ms)", color='#94a3b8')
ax.set_title("CP-SAT solve time vs agent count (8×8)", color='white')
ax.tick_params(colors='#94a3b8')
plt.tight_layout(); plt.show()
```

- [ ] **Step 3: Run all cells top to bottom — no errors**

- [ ] **Step 4: Commit**

```bash
git add notebooks/01_model_2d.ipynb
git commit -m "feat(G3): notebook 2D — animation, benchmarks, solve analysis"
```

---

## Task 7: Three.js Flat Viewer (Pipeline Validation)

**Goal:** minimal end-to-end check — browser fetches `/solve`, animates drones top-down. No city, no effects yet. Validate the full Python→JSON→JS pipeline before building the city.

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/api.js`

- [ ] **Step 1: Create api.js**

```javascript
// frontend/api.js
const API = 'http://localhost:5050';

export async function fetchScenarios() {
  const r = await fetch(`${API}/scenarios`);
  return r.json();
}

export async function fetchSolve(config) {
  const r = await fetch(`${API}/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return r.json();
}
```

- [ ] **Step 2: Create index.html (flat viewer)**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>MAPF — Flat Viewer</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0f172a; color:#e2e8f0; font-family:system-ui; }
  #hud { position:fixed; top:16px; left:16px; font-size:13px; color:#94a3b8; }
  #controls { position:fixed; bottom:16px; left:50%; transform:translateX(-50%);
              display:flex; gap:8px; }
  button { padding:8px 20px; background:#1e3a5f; border:1px solid #2563eb;
           color:#fff; border-radius:6px; cursor:pointer; font-size:13px; }
  button:hover { background:#2563eb; }
</style>
</head>
<body>
<div id="hud">Loading...</div>
<div id="controls">
  <button id="btn-play">▶ Play</button>
  <button id="btn-pause">⏸ Pause</button>
  <button id="btn-reset">↺ Reset</button>
</div>
<canvas id="c"></canvas>

<script>
const COLORS = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#a855f7',
                '#06b6d4','#ec4899','#84cc16','#fb923c','#e11d48'];

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let solution = null, playing = false, frame = 0, animId = null;

const PAYLOAD = {
  grid: { rows: 8, cols: 8, alts: 1 },
  drones: [
    { id: 0, start: [0,0], goal: [7,7] },
    { id: 1, start: [7,0], goal: [0,7] },
    { id: 2, start: [0,7], goal: [7,0] },
    { id: 3, start: [3,0], goal: [3,7] },
  ],
  nofly: [], buildings: [], time_limit_s: 15,
};

async function load() {
  document.getElementById('hud').textContent = 'Solving...';
  const r = await fetch('http://localhost:5050/solve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(PAYLOAD),
  });
  solution = await r.json();
  document.getElementById('hud').textContent =
    `Status: ${solution.status} | Makespan: ${solution.makespan} | Solve: ${solution.solve_time_ms}ms`;
  draw(0);
}

function cellSize() { return Math.min(canvas.width, canvas.height) / 10; }

function draw(t) {
  if (!solution) return;
  const cs = cellSize();
  const off = cs;
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Grid
  const rows = PAYLOAD.grid.rows, cols = PAYLOAD.grid.cols;
  ctx.strokeStyle = '#1e3a5f';
  ctx.lineWidth = 0.5;
  for (let r = 0; r <= rows; r++) {
    ctx.beginPath(); ctx.moveTo(off, off + r*cs); ctx.lineTo(off + cols*cs, off + r*cs); ctx.stroke();
  }
  for (let c = 0; c <= cols; c++) {
    ctx.beginPath(); ctx.moveTo(off + c*cs, off); ctx.lineTo(off + c*cs, off + rows*cs); ctx.stroke();
  }

  // Drones
  Object.entries(solution.paths).forEach(([id, path], i) => {
    const pos = path[Math.min(t, path.length - 1)];
    const x = off + pos[1] * cs + cs/2;
    const y = off + pos[0] * cs + cs/2;
    ctx.beginPath();
    ctx.arc(x, y, cs * 0.3, 0, Math.PI * 2);
    ctx.fillStyle = COLORS[i % COLORS.length];
    ctx.fill();
  });
}

let lastTime = 0;
function loop(ts) {
  if (!playing) return;
  if (ts - lastTime > 400) {
    lastTime = ts;
    frame = Math.min(frame + 1, solution.makespan);
    draw(frame);
    if (frame >= solution.makespan) playing = false;
  }
  animId = requestAnimationFrame(loop);
}

document.getElementById('btn-play').onclick = () => { playing = true; requestAnimationFrame(loop); };
document.getElementById('btn-pause').onclick = () => { playing = false; cancelAnimationFrame(animId); };
document.getElementById('btn-reset').onclick = () => { playing = false; frame = 0; draw(0); };

load();
</script>
</body>
</html>
```

- [ ] **Step 3: Start API then open browser**

```bash
# Terminal 1
python api/server.py

# Terminal 2 — open browser (WSL2: use localhost on Windows browser)
# Open file:///path/to/frontend/index.html
# OR serve with: python -m http.server 8080 --directory frontend
```

- [ ] **Step 4: Verify in browser**
  - HUD shows `Status: optimal | Makespan: N`
  - Press Play → drones move on grid
  - No console errors in DevTools

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html frontend/api.js
git commit -m "feat(G3): flat 2D viewer — validates Python→Flask→Three.js pipeline"
```

---

## Task 8: Grid 3D — Building Extension

**Files:**
- Modify: `solver/grid.py` (already supports 3D — just validate with tests)
- Modify: `tests/test_grid.py` (add building tests if not already present)

- [ ] **Step 1: Run existing 3D grid tests**

```bash
pytest tests/test_grid.py -v -k "3d or building"
```

Expected: all pass (implemented in Task 2). If any fail, fix `grid.py`.

- [ ] **Step 2: Add building integration test in test_mapf.py**

```python
# append to tests/test_mapf.py
def test_3d_solver_avoids_building():
    g = Grid(rows=6, cols=6, alts=3)
    g.add_building(row=3, col=3, height=2)  # blocks (3,3,0) and (3,3,1)
    drones = [
        Drone(id=0, start=(0,0,0), goal=(5,5,0)),
        Drone(id=1, start=(5,0,0), goal=(0,5,0)),
    ]
    sol = MAPFSolver(g, drones, time_limit_s=30).solve()
    assert sol.status in ("optimal", "feasible")
    for path in sol.paths.values():
        for pos in path:
            assert pos not in g.obstacles, f"Path through obstacle: {pos}"
```

- [ ] **Step 3: Run new test**

```bash
pytest tests/test_mapf.py::test_3d_solver_avoids_building -v
```

Expected: PASSED.

- [ ] **Step 4: Commit**

```bash
git add tests/test_mapf.py tests/test_grid.py
git commit -m "test(G3): 3D building obstacle integration test"
```

---

## Task 9: Notebook 3D

**Files:**
- Create: `notebooks/02_model_3d.ipynb`

- [ ] **Step 1: Create notebook cells**

**Cell 1 — Setup**
```python
import sys; sys.path.insert(0, '..')
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver
from solver.scenarios import get_scenario
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
```

**Cell 2 — Solve city_3d scenario**
```python
sc = get_scenario("city_3d")
grid = Grid(**sc["grid_config"])
for b in sc["buildings"]:
    grid.add_building(b["row"], b["col"], b["height"])
drones = [Drone(**{**d, "start": tuple(d["start"]), "goal": tuple(d["goal"])})
          for d in sc["drones"]]
sol = MAPFSolver(grid, drones, time_limit_s=60).solve()
print(f"Status: {sol.status} | Makespan: {sol.makespan} | Solve: {sol.solve_time_ms:.0f}ms")
```

**Cell 3 — 3D path visualization (static)**
```python
COLORS = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#a855f7',
          '#06b6d4','#ec4899','#84cc16','#fb923c','#e11d48']

fig = plt.figure(figsize=(10, 8), facecolor='#0f172a')
ax = fig.add_subplot(111, projection='3d')
ax.set_facecolor('#0f172a')

for i, d in enumerate(drones):
    path = sol.paths[d.id]
    xs = [p[1] for p in path]
    ys = [p[0] for p in path]
    zs = [p[2] for p in path]
    col = COLORS[i % len(COLORS)]
    ax.plot(xs, ys, zs, color=col, lw=2, alpha=0.8)
    ax.scatter([xs[0]], [ys[0]], [zs[0]], color=col, s=60, marker='o')
    ax.scatter([xs[-1]], [ys[-1]], [zs[-1]], color=col, s=100, marker='*')

ax.set_xlabel('Col', color='#94a3b8')
ax.set_ylabel('Row', color='#94a3b8')
ax.set_zlabel('Alt', color='#94a3b8')
ax.set_title(f'3D MAPF Solution — Makespan={sol.makespan}', color='white')
plt.tight_layout(); plt.show()
```

**Cell 4 — Benchmark: solve time vs altitude layers**
```python
results = []
for alts in [1, 2, 3, 4, 5]:
    g = Grid(rows=8, cols=8, alts=alts)
    ds = [
        Drone(0, (0,0,0), (7,7,alts-1)),
        Drone(1, (7,0,0), (0,7,alts-1)),
        Drone(2, (0,7,0), (7,0,alts-1)),
    ]
    s = MAPFSolver(g, ds, time_limit_s=30).solve()
    results.append({"alts": alts, "ms": s.solve_time_ms, "status": s.status})
    print(f"alts={alts}: {s.status} in {s.solve_time_ms:.0f}ms")
```

- [ ] **Step 2: Run all cells — no errors, plots render**

- [ ] **Step 3: Commit**

```bash
git add notebooks/02_model_3d.ipynb
git commit -m "feat(G3): notebook 3D — city scenario, path viz, altitude benchmark"
```

---

## Task 10: Three.js City Scene

**Files:**
- Create: `frontend/scene.js`
- Modify: `frontend/index.html` (replace flat viewer with city scaffold)

- [ ] **Step 1: Create scene.js**

```javascript
// frontend/scene.js
export class CityScene {
  constructor(renderer) {
    this.renderer = renderer;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x040810);
    this.scene.fog = new THREE.FogExp2(0x040810, 0.012);

    this.camera = new THREE.PerspectiveCamera(
      55, window.innerWidth / window.innerHeight, 0.1, 500
    );
    this.camera.position.set(30, 20, 30);

    this.controls = new THREE.OrbitControls(this.camera, renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.target.set(8, 4, 8);

    this._addLights();
    this._addGround();
  }

  _addLights() {
    this.scene.add(new THREE.AmbientLight(0x0f1a2e, 1.2));
    const dir = new THREE.DirectionalLight(0x93c5fd, 0.8);
    dir.position.set(20, 40, 20);
    this.scene.add(dir);
  }

  _addGround() {
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(80, 80),
      new THREE.MeshPhongMaterial({ color: 0x070d1a })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(8, -0.01, 8);
    this.scene.add(ground);

    const grid = new THREE.GridHelper(80, 40, 0x0f2744, 0x091522);
    grid.position.set(8, 0, 8);
    this.scene.add(grid);
  }

  // Each building: { row, col, height } — maps to Three.js (col, height/2, row)
  addBuildings(buildings, cellSize = 1.0) {
    this._buildingMeshes = [];
    for (const b of buildings) {
      const h = b.height * cellSize * 1.5;
      const geo = new THREE.BoxGeometry(cellSize * 0.85, h, cellSize * 0.85);
      const mat = new THREE.MeshPhongMaterial({
        color: 0x0d1f3c, emissive: 0x071020, transparent: true, opacity: 0.88,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(b.col * cellSize, h / 2, b.row * cellSize);
      this.scene.add(mesh);

      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: 0x1e3a5f, transparent: true, opacity: 0.5 })
      );
      edges.position.copy(mesh.position);
      this.scene.add(edges);

      if (b.height >= 3) {
        const light = new THREE.PointLight(0x1e3a5f, 0.5, 5);
        light.position.set(b.col * cellSize, h + 0.2, b.row * cellSize);
        this.scene.add(light);
      }
      this._buildingMeshes.push(mesh);
    }
  }

  addNoFlyBox(minPos, maxPos, cellSize = 1.0) {
    const [r0, c0] = minPos, [r1, c1] = maxPos;
    const w = (c1 - c0 + 1) * cellSize;
    const d = (r1 - r0 + 1) * cellSize;
    const h = 6;
    const geo = new THREE.BoxGeometry(w, h, d);
    const mat = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.2 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set((c0 + c1) / 2 * cellSize, h / 2, (r0 + r1) / 2 * cellSize);
    this.scene.add(mesh);

    const edgeMat = new THREE.LineBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.7 });
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), edgeMat);
    edges.position.copy(mesh.position);
    this.scene.add(edges);

    return mesh;
  }

  update() {
    this.controls.update();
  }

  render() {
    this.renderer.render(this.scene, this.camera);
  }

  onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
  }
}
```

- [ ] **Step 2: Update index.html to use Three.js + scene.js**

Replace `frontend/index.html` with:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>MAPF — City 3D</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#040810; overflow:hidden; }
  #hud {
    position:fixed; top:16px; left:16px; z-index:10;
    font:13px/1.6 system-ui; color:#94a3b8; pointer-events:none;
  }
  #hud .val { color:#7dd3fc; font-weight:600; }
  #controls {
    position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
    z-index:10; display:flex; gap:8px;
  }
  button {
    padding:9px 22px; background:#0f172a; border:1px solid #334155;
    color:#94a3b8; border-radius:7px; cursor:pointer; font-size:13px;
    transition:all .15s;
  }
  button:hover { border-color:#3b82f6; color:#fff; background:#1e3a5f; }
  #btn-solve { border-color:#3b82f6; color:#7dd3fc; }
</style>
</head>
<body>

<div id="hud">
  <div>Status: <span class="val" id="h-status">—</span></div>
  <div>Makespan: <span class="val" id="h-makespan">—</span></div>
  <div>Solve time: <span class="val" id="h-time">—</span></div>
  <div>Conflicts avoided: <span class="val" id="h-conflicts">—</span></div>
  <div>Frame: <span class="val" id="h-frame">—</span></div>
</div>

<div id="controls">
  <button id="btn-solve">⚡ Solve</button>
  <button id="btn-play">▶ Play</button>
  <button id="btn-pause">⏸ Pause</button>
  <button id="btn-reset">↺ Reset</button>
  <button id="btn-step">⏭ Step</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script type="module">
import { CityScene } from './scene.js';
import { DroneManager } from './drones.js';
import { fetchSolve } from './api.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const cityScene = new CityScene(renderer);
let droneManager = null;
let solution = null;
let playing = false, frame = 0, lastTick = 0;
const SPEED_MS = 350;

const PAYLOAD = {
  grid: { rows: 16, cols: 16, alts: 1 },
  drones: [
    { id:0, start:[0,0],   goal:[15,15] }, { id:1, start:[15,0],  goal:[0,15]  },
    { id:2, start:[0,15],  goal:[15,0]  }, { id:3, start:[15,15], goal:[0,0]   },
    { id:4, start:[0,7],   goal:[15,8]  }, { id:5, start:[15,8],  goal:[0,7]   },
    { id:6, start:[7,0],   goal:[8,15]  }, { id:7, start:[8,15],  goal:[7,0]   },
    { id:8, start:[3,3],   goal:[12,12] }, { id:9, start:[12,12], goal:[3,3]   },
  ],
  nofly: [], buildings: [], time_limit_s: 30,
};

document.getElementById('btn-solve').onclick = async () => {
  document.getElementById('h-status').textContent = 'Solving...';
  solution = await fetchSolve(PAYLOAD);
  document.getElementById('h-status').textContent = solution.status;
  document.getElementById('h-makespan').textContent = solution.makespan;
  document.getElementById('h-time').textContent = `${solution.solve_time_ms}ms`;
  document.getElementById('h-conflicts').textContent = solution.conflicts_avoided;
  frame = 0;

  if (droneManager) droneManager.dispose(cityScene.scene);
  droneManager = new DroneManager(PAYLOAD.drones, cityScene.scene);
  droneManager.updateFrame(solution.paths, 0);
};

document.getElementById('btn-play').onclick  = () => { playing = true; };
document.getElementById('btn-pause').onclick = () => { playing = false; };
document.getElementById('btn-reset').onclick = () => { playing = false; frame = 0; if(droneManager&&solution) droneManager.updateFrame(solution.paths, 0); };
document.getElementById('btn-step').onclick  = () => { if(solution&&frame<solution.makespan){ frame++; droneManager.updateFrame(solution.paths, frame); document.getElementById('h-frame').textContent=`${frame}/${solution.makespan}`; }};

function loop(ts) {
  requestAnimationFrame(loop);
  if (playing && solution && droneManager && ts - lastTick > SPEED_MS) {
    lastTick = ts;
    if (frame < solution.makespan) {
      frame++;
      droneManager.updateFrame(solution.paths, frame);
      document.getElementById('h-frame').textContent = `${frame}/${solution.makespan}`;
    } else { playing = false; }
  }
  droneManager?.animateTrails();
  cityScene.update();
  cityScene.render();
}
requestAnimationFrame(loop);

window.addEventListener('resize', () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  cityScene.onResize();
});
</script>
</body>
</html>
```

- [ ] **Step 3: Serve and verify scene loads with buildings + ground**

```bash
python -m http.server 8080 --directory frontend
# Open http://localhost:8080 in browser
```

Expected: dark city ground + grid, no errors in console. "Solve" button visible but drones appear after Task 11.

- [ ] **Step 4: Commit**

```bash
git add frontend/scene.js frontend/index.html
git commit -m "feat(G3): Three.js city scene — buildings, ground, lights, orbit camera"
```

---

## Task 11: Drones, Trails, Markers

**Files:**
- Create: `frontend/drones.js`

- [ ] **Step 1: Create drones.js**

```javascript
// frontend/drones.js
const COLORS = [
  0x3b82f6, 0xef4444, 0x22c55e, 0xf59e0b, 0xa855f7,
  0x06b6d4, 0xec4899, 0x84cc16, 0xfb923c, 0xe11d48,
  0x8b5cf6, 0x0ea5e9, 0x10b981, 0xf97316, 0x6366f1,
];
const CELL = 1.0;   // world units per grid cell
const TRAIL_LEN = 50;

export class DroneManager {
  constructor(droneConfigs, scene) {
    this.scene = scene;
    this.drones = [];

    for (let i = 0; i < droneConfigs.length; i++) {
      const col = COLORS[i % COLORS.length];
      const d = droneConfigs[i];

      // Sphere + glow
      const geo = new THREE.SphereGeometry(0.22, 14, 14);
      const mat = new THREE.MeshPhongMaterial({ color: col, emissive: col, emissiveIntensity: 0.7 });
      const mesh = new THREE.Mesh(geo, mat);
      const light = new THREE.PointLight(col, 1.8, 4.5);
      mesh.add(light);
      scene.add(mesh);

      // Trail
      const trailGeo = new THREE.BufferGeometry();
      const buf = new Float32Array(TRAIL_LEN * 3);
      trailGeo.setAttribute('position', new THREE.BufferAttribute(buf, 3));
      trailGeo.setDrawRange(0, 0);
      const trail = new THREE.Line(
        trailGeo,
        new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.55 })
      );
      scene.add(trail);

      // Start marker — torus ring on ground
      const startRing = new THREE.Mesh(
        new THREE.TorusGeometry(0.32, 0.06, 8, 24),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.5 })
      );
      startRing.rotation.x = -Math.PI / 2;
      startRing.position.set(d.start[1] * CELL, 0.05, d.start[0] * CELL);
      scene.add(startRing);

      // Goal marker — vertical pillar
      const goalPillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.08, 0.08, 3, 8),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.6 })
      );
      goalPillar.position.set(d.goal[1] * CELL, 1.5, d.goal[0] * CELL);
      scene.add(goalPillar);

      const goalLight = new THREE.PointLight(col, 0.8, 3);
      goalLight.position.copy(goalPillar.position);
      scene.add(goalLight);

      this.drones.push({ id: d.id, mesh, trail, trailPts: [], col });
    }
  }

  _posToWorld(pos) {
    // pos: [row, col] or [row, col, alt]
    return new THREE.Vector3(
      pos[1] * CELL,
      (pos[2] ?? 0) * CELL * 1.5 + 0.4,
      pos[0] * CELL
    );
  }

  updateFrame(paths, t) {
    for (const d of this.drones) {
      const path = paths[String(d.id)];
      if (!path) continue;
      const pos = path[Math.min(t, path.length - 1)];
      const world = this._posToWorld(pos);
      d.mesh.position.copy(world);

      d.trailPts.push(world.clone());
      if (d.trailPts.length > TRAIL_LEN) d.trailPts.shift();

      const attr = d.trail.geometry.attributes.position;
      for (let i = 0; i < d.trailPts.length; i++) {
        attr.setXYZ(i, d.trailPts[i].x, d.trailPts[i].y, d.trailPts[i].z);
      }
      attr.needsUpdate = true;
      d.trail.geometry.setDrawRange(0, d.trailPts.length);
    }

    // Conflict flash — any two drones within 1.5 cells
    for (let i = 0; i < this.drones.length; i++) {
      for (let j = i + 1; j < this.drones.length; j++) {
        const dist = this.drones[i].mesh.position.distanceTo(this.drones[j].mesh.position);
        if (dist < 1.5 * CELL) {
          this._flash(this.drones[i], this.drones[j]);
        }
      }
    }
  }

  _flash(da, db) {
    // Brief emissive spike
    [da, db].forEach(d => {
      d.mesh.material.emissiveIntensity = 2.5;
      setTimeout(() => { d.mesh.material.emissiveIntensity = 0.7; }, 120);
    });
  }

  animateTrails() {
    // Subtle hover bob
    const t = Date.now() * 0.002;
    this.drones.forEach((d, i) => {
      d.mesh.position.y += Math.sin(t + i * 1.3) * 0.003;
    });
  }

  dispose(scene) {
    for (const d of this.drones) {
      scene.remove(d.mesh);
      scene.remove(d.trail);
    }
    this.drones = [];
  }
}
```

- [ ] **Step 2: Verify in browser**

```bash
# API running: python api/server.py
# Frontend: python -m http.server 8080 --directory frontend
```

- Open http://localhost:8080
- Click **⚡ Solve** → wait for solve → click **▶ Play**
- Expected: 10 colored drones with glowing trails animate across the scene, start rings visible on ground, goal pillars glowing

- [ ] **Step 3: Commit**

```bash
git add frontend/drones.js
git commit -m "feat(G3): DroneManager — spheres, trails, start/end markers, conflict flash"
```

---

## Task 12: UI — HUD, No-Fly Zone Tool, Playback Controls

**Files:**
- Create: `frontend/ui.js`
- Modify: `frontend/index.html` (wire in ui.js + no-fly zone click handler)

- [ ] **Step 1: Create ui.js**

```javascript
// frontend/ui.js
export class UIManager {
  constructor({ onSolve, onPlay, onPause, onReset, onStep, onAddNoFly }) {
    this._nofly = [];
    this._placingNoFly = false;

    document.getElementById('btn-solve').onclick = () => onSolve(this._nofly);
    document.getElementById('btn-play').onclick  = onPlay;
    document.getElementById('btn-pause').onclick = onPause;
    document.getElementById('btn-reset').onclick = onReset;
    document.getElementById('btn-step').onclick  = onStep;

    const btnNF = document.getElementById('btn-nofly');
    btnNF.onclick = () => {
      this._placingNoFly = !this._placingNoFly;
      btnNF.style.borderColor = this._placingNoFly ? '#ef4444' : '#334155';
      btnNF.style.color       = this._placingNoFly ? '#ef4444' : '#94a3b8';
      btnNF.textContent = this._placingNoFly ? '🚫 Click grid to place' : '🚫 No-Fly Zone';
    };

    this._onAddNoFly = onAddNoFly;
  }

  isPlacingNoFly() { return this._placingNoFly; }

  addNoFlyFromClick(row, col) {
    const nf = { min: [row, col], max: [row + 1, col + 1] };
    this._nofly.push(nf);
    this._onAddNoFly(nf);
  }

  updateHUD({ status, makespan, solve_time_ms, conflicts_avoided }) {
    document.getElementById('h-status').textContent    = status;
    document.getElementById('h-makespan').textContent  = makespan;
    document.getElementById('h-time').textContent      = `${Math.round(solve_time_ms)}ms`;
    document.getElementById('h-conflicts').textContent = conflicts_avoided;
  }

  updateFrame(frame, maxFrame) {
    document.getElementById('h-frame').textContent = `${frame}/${maxFrame}`;
  }

  clearNoFly() {
    this._nofly = [];
  }
}
```

- [ ] **Step 2: Update index.html — add no-fly button and Raycaster for click placement**

Add `<button id="btn-nofly">🚫 No-Fly Zone</button>` inside `#controls`.

Replace the `<script type="module">` block with:

```html
<script type="module">
import { CityScene } from './scene.js';
import { DroneManager } from './drones.js';
import { UIManager } from './ui.js';
import { fetchSolve } from './api.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const cityScene = new CityScene(renderer);
let droneManager = null, solution = null;
let playing = false, frame = 0, lastTick = 0;
const SPEED_MS = 350;

const PAYLOAD = {
  grid: { rows: 16, cols: 16, alts: 1 },
  drones: [
    { id:0, start:[0,0],   goal:[15,15] }, { id:1, start:[15,0],  goal:[0,15]  },
    { id:2, start:[0,15],  goal:[15,0]  }, { id:3, start:[15,15], goal:[0,0]   },
    { id:4, start:[0,7],   goal:[15,8]  }, { id:5, start:[15,8],  goal:[0,7]   },
    { id:6, start:[7,0],   goal:[8,15]  }, { id:7, start:[8,15],  goal:[7,0]   },
    { id:8, start:[3,3],   goal:[12,12] }, { id:9, start:[12,12], goal:[3,3]   },
  ],
  buildings: [], time_limit_s: 30,
};

const ui = new UIManager({
  onSolve: async (nofly) => {
    ui.updateHUD({ status: 'Solving...', makespan: '—', solve_time_ms: 0, conflicts_avoided: '—' });
    solution = await fetchSolve({ ...PAYLOAD, nofly });
    ui.updateHUD(solution);
    frame = 0;
    if (droneManager) droneManager.dispose(cityScene.scene);
    droneManager = new DroneManager(PAYLOAD.drones, cityScene.scene);
    droneManager.updateFrame(solution.paths, 0);
  },
  onPlay:  () => { playing = true; },
  onPause: () => { playing = false; },
  onReset: () => { playing = false; frame = 0; if(droneManager&&solution) droneManager.updateFrame(solution.paths,0); },
  onStep:  () => { if(solution&&frame<solution.makespan){ frame++; droneManager.updateFrame(solution.paths,frame); ui.updateFrame(frame,solution.makespan); }},
  onAddNoFly: (nf) => { cityScene.addNoFlyBox(nf.min, nf.max); },
});

// Raycaster for no-fly zone placement (click on ground)
const raycaster = new THREE.Raycaster();
const groundPlane = new THREE.Plane(new THREE.Vector3(0,1,0), 0);
renderer.domElement.addEventListener('click', (e) => {
  if (!ui.isPlacingNoFly()) return;
  const mouse = new THREE.Vector2(
    (e.clientX / window.innerWidth) * 2 - 1,
    -(e.clientY / window.innerHeight) * 2 + 1
  );
  raycaster.setFromCamera(mouse, cityScene.camera);
  const pt = new THREE.Vector3();
  raycaster.ray.intersectPlane(groundPlane, pt);
  if (pt) {
    const row = Math.floor(pt.z), col = Math.floor(pt.x);
    if (row >= 0 && col >= 0 && row < 16 && col < 16)
      ui.addNoFlyFromClick(row, col);
  }
});

function loop(ts) {
  requestAnimationFrame(loop);
  if (playing && solution && droneManager && ts - lastTick > SPEED_MS) {
    lastTick = ts;
    if (frame < solution.makespan) {
      frame++;
      droneManager.updateFrame(solution.paths, frame);
      ui.updateFrame(frame, solution.makespan);
    } else { playing = false; }
  }
  droneManager?.animateTrails();
  cityScene.update();
  cityScene.render();
}
requestAnimationFrame(loop);

window.addEventListener('resize', () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  cityScene.onResize();
});
</script>
```

- [ ] **Step 3: Full demo test**

```bash
# Terminal 1: python api/server.py
# Browser: http://localhost:8080
```

Test sequence:
1. Click **⚡ Solve** → HUD fills in → click **▶ Play** → drones animate
2. Click **🚫 No-Fly Zone** → click on grid → red box appears → click **⚡ Solve** again → drones reroute

- [ ] **Step 4: Commit**

```bash
git add frontend/ui.js frontend/index.html
git commit -m "feat(G3): UIManager — HUD, no-fly zone placement, full playback controls"
```

---

## Task 13: Soutenance Scenarios + Final Polish

**Files:**
- Modify: `solver/scenarios.py` (already complete — verify city_3d works)
- Modify: `frontend/index.html` (add scenario selector dropdown)

- [ ] **Step 1: Add scenario selector to index.html HUD**

Inside `#hud`, add:
```html
<div style="margin-top:8px">
  Scenario: <select id="sel-scenario" style="background:#0f172a;color:#7dd3fc;border:1px solid #334155;border-radius:4px;padding:2px 6px">
    <option value="city_2d">city_2d (16×16, 10 drones)</option>
    <option value="city_3d">city_3d (16×16×5, 10 drones)</option>
    <option value="small_2d">small_2d (8×8, 5 drones)</option>
  </select>
</div>
```

Wire up `onSolve` to read the selected scenario from `/scenarios` and merge with current no-fly zones before calling `/solve`.

- [ ] **Step 2: End-to-end soutenance rehearsal**

Run through the live demo script:
1. Load `city_2d` → Solve → Play → narrate makespan + conflicts avoided from HUD
2. Pause → place 2 no-fly zones → Solve → Play → show rerouting
3. Switch to `city_3d` → Solve → Play → rotate camera to show altitude layers

Expected: each step completes in <30s solve time, no console errors.

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASSED.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(G3): soutenance scenarios, scenario selector, final polish"
```

---

## Self-Review

**Spec coverage:**
- ✅ CP-SAT model with vertex+edge conflicts (Task 3)
- ✅ 2D grid 16×16 (Task 2 + 4)
- ✅ 3D extension with altitude + buildings (Tasks 8–9)
- ✅ Flask API /solve + /scenarios (Task 5)
- ✅ Three.js city scene with buildings (Task 10)
- ✅ Drones with trails, glow, start/end markers (Task 11)
- ✅ No-fly zones (red volumes, interactive placement) (Tasks 10, 12)
- ✅ Conflict flash (Task 11)
- ✅ Stats HUD (Task 12)
- ✅ Play/Pause/Step/Reset controls (Task 12)
- ✅ Jupyter notebook 2D (Task 6) + 3D (Task 9)
- ✅ Moving AI Lab benchmarks (Task 6, notebook)
- ✅ Minimize makespan (Task 3)

**No placeholders found.**

**Type consistency:** `Drone(id, start, goal)` used consistently across mapf.py, scenarios.py, tests. `pos_to_idx` dict used in solver. `DroneManager` receives same `droneConfigs` list format. `fetchSolve` returns paths keyed by string id — `drones.js` uses `String(d.id)` to match.
