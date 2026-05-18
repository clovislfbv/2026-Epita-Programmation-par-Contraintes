# Design Spec — G3 MAPF Drone Coordination
**Date:** 2026-04-22
**Authors:** Matteo Atkinson & Paul Witkowski
**Course:** EPITA 2026 — Programmation par Contraintes

---

## 1. Problem Summary

Multi-Agent Path Finding (MAPF): compute collision-free, optimal trajectories for a set of drones sharing a 3D urban airspace. Each drone has a start and a goal position. No two drones may occupy the same position at the same time (vertex conflict), nor swap positions in the same timestep (edge conflict). The problem is NP-hard and is modelled with Google OR-Tools CP-SAT.

---

## 2. Decided Stack

| Component | Choice |
|-----------|--------|
| Solver | Google OR-Tools CP-SAT (Python) |
| Backend | Flask (local API server, ~50 lines) |
| Frontend | Three.js (3D city scene, orbit controls) |
| Official deliverable | Jupyter Notebook (2D + JSON export) |
| 2D grid | 16×16, 10–15 drones, minimize makespan |
| 3D extension | 16×16×5 altitude levels, buildings as volumetric obstacles |

---

## 3. CP-SAT Model

### Variables
Binary variables `x[a, p, t] ∈ {0, 1}` — agent `a` is at position `p` at timestep `t`.

Positions are `(row, col)` for 2D and `(row, col, alt)` for 3D.

### Constraints

| Constraint | Expression |
|-----------|------------|
| Presence | `∀a,t: sum_p(x[a,p,t]) == 1` |
| Movement | `x[a,p,t]==1 → x[a, neighbors(p)∪{p}, t+1] == 1` |
| Vertex conflict | `∀p,t: sum_a(x[a,p,t]) <= 1` |
| Edge conflict | `∀a,b,p,q,t: x[a,p,t]+x[b,q,t]+x[a,q,t+1]+x[b,p,t+1] <= 3` |
| Goal | `∀a: x[a, goal(a), makespan] == 1` |
| No-fly zones | positions in no-fly zones removed from domain before solve |

### Objective
Minimize **makespan** = the timestep at which the last drone reaches its goal.

### 2D → 3D Extension
Positions extend from `(row, col)` to `(row, col, alt)`. Neighbors include `±alt`. Buildings occupy specific `(row, col, 0..height)` positions and are excluded from the position domain. The CP-SAT model is identical — only the position graph changes.

---

## 4. Project Structure

```
groupe-G3-Coordination_de_drones_par_Multi-Agent_Path_Finding/
│
├── solver/
│   ├── mapf.py          # CP-SAT model — variables, constraints, solve()
│   ├── grid.py          # 2D/3D grid, neighbors, obstacles, no-fly zones
│   └── scenarios.py     # Preset scenarios (Moving AI benchmarks + custom city)
│
├── api/
│   └── server.py        # Flask — POST /solve, GET /scenarios
│
├── frontend/
│   ├── index.html       # Three.js app entry point
│   ├── scene.js         # 3D city, buildings, camera, orbit controls
│   ├── drones.js        # Spheres, glow trails, start/end markers
│   ├── ui.js            # HUD stats, no-fly zone placement, playback controls
│   └── api.js           # fetch() calls to Flask
│
├── notebooks/
│   ├── 01_model_2d.ipynb      # 2D CP-SAT model, benchmarks, matplotlib animation
│   └── 02_model_3d.ipynb      # 3D extension, city scenarios, analysis
│
└── benchmarks/
    └── maps/            # Moving AI Lab .map files
```

---

## 5. Flask API Contract

### `POST /solve`
```json
Request:
{
  "grid": { "rows": 16, "cols": 16, "alts": 1 },
  "drones": [
    { "id": 0, "start": [0, 0, 0], "goal": [15, 15, 3] },
    ...
  ],
  "nofly": [
    { "min": [5, 5, 0], "max": [7, 7, 2] }
  ],
  "time_limit_s": 10
}

Response:
{
  "status": "optimal",
  "makespan": 24,
  "solve_time_ms": 1340,
  "conflicts_avoided": 7,    // vertex+edge conflicts actively resolved by CP-SAT (counted during constraint propagation)
  "paths": {
    "0": [[0,0,0], [1,0,0], [2,0,0], ...],
    "1": [[15,0,15], [14,0,15], ...]
  }
}
```

### `GET /scenarios`
Returns list of preset scenario names and metadata.

---

## 6. Three.js Frontend

### Visual Elements

| Element | Implementation |
|---------|---------------|
| City buildings | `BoxGeometry` varying heights, `EdgesGeometry` for wireframe glow, `PointLight` on rooftops >8u |
| Drones | `SphereGeometry(0.22)` + `MeshPhongMaterial` emissive + `PointLight` attached |
| Trails | `BufferGeometry` line, last 60–80 positions, same color as drone, opacity 0.6 |
| Start markers | Colored ring (`TorusGeometry`) on ground at start position |
| End markers | Colored vertical pillar (`CylinderGeometry`) at goal position |
| No-fly zones | `BoxGeometry` red, `MeshBasicMaterial` transparent opacity 0.25, clickable to place |
| Conflict flash | Brief white `PointLight` spike when two drones pass within 1.5 cells |
| Stats HUD | DOM overlay — makespan, solve time, conflicts avoided, per-drone progress bar |

### Playback Controls
Play / Pause / Step-forward / Speed ×0.5 ×1 ×2 ×5 / Reset / Re-solve

### Live Demo Flow (soutenance, ~2 min)
1. Load city scene with 10 drones, press Play → drones animate to goals
2. Click to place a no-fly zone mid-trajectory → press Re-solve → paths update live
3. Switch to 3D altitude view — drones navigate above and between buildings

---

## 7. Development Phases

### Phase 1 — Core solver 2D
- `grid.py`: 16×16 grid, neighbor function, obstacle masking, no-fly zone support
- `mapf.py`: full CP-SAT model (presence, movement, vertex conflict, edge conflict, makespan objective)
- Validate on small cases (4×4, 3 drones) with known optimal solutions
- Notebook `01_model_2d.ipynb`: matplotlib `FuncAnimation`, Moving AI Lab benchmarks, solve time vs. agent count analysis

### Phase 2 — Flask + Three.js 2D viewer
- `server.py`: Flask with `/solve` and `/scenarios` endpoints
- `index.html` + `scene.js`: flat top-down Three.js scene, drones animated from path JSON
- Validate full round-trip: Python solve → JSON → browser animation

### Phase 3 — 3D extension
- `grid.py`: extend positions to `(row, col, alt)`, 3D neighbor function, building height map
- `mapf.py`: unchanged model, larger position domain
- Notebook `02_model_3d.ipynb`: 3D analysis, solve time vs. altitude layers

### Phase 4 — City scene + full visual effects
- `scene.js`: buildings with heights, rooftop lights, fog, ground grid
- `drones.js`: trails, start/end markers, conflict flash
- `ui.js`: no-fly zone placement (click on scene), HUD stats overlay, playback controls
- Custom soutenance scenarios in `scenarios.py`

---

## 8. Open Decisions Resolved

| Decision | Resolution |
|----------|------------|
| Space model | 2D grid first → 3D grid with altitude (building heights as obstacles) |
| Optimization metric | Makespan (minimize max arrival time) |
| Additional constraints | No-fly zones (NOTAM analog), vertex + edge conflicts |
| Benchmark set | Moving AI Lab grid-based maps + custom city scenarios |

---

## 9. Out of Scope

- Dynamic weather zones (considered, excluded — adds complexity without CP-SAT value for the course)
- ATC separation constraints (continuous min-distance) — 3D grid discretization makes this implicit
- Real drone hardware integration
- Multi-robot warehouse (Annex #12) — explicitly different from this subject
