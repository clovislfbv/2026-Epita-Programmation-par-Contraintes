# Scenarios Refactor + Variable Map Sizes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move scenarios to JSON files in a `scenarios/` folder, load them dynamically in the backend, fetch them from the frontend, and replace all current presets with 5 new scenarios of varying sizes.

**Architecture:** A new `api/scenario_loader.py` scans `scenarios/*.json` at startup; `GET /scenarios` returns the full list; the frontend fetches it on load, rebuilds the Three.js scene dimensions per scenario, and auto-repositions the camera. `solver/scenarios.py` is deleted.

**Tech Stack:** Python / Flask, Three.js r128, JSON, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scenarios/micro_flat.json` | 4×4×1, 3 drones |
| Create | `scenarios/micro_3d.json` | 4×4×3, 4 drones, 2 buildings |
| Create | `scenarios/medium_flat.json` | 6×8×1, 5 drones (non-square) |
| Create | `scenarios/medium_city.json` | 8×6×3, 6 drones, 3 buildings (non-square) |
| Create | `scenarios/big_city.json` | 10×10×3, 8 drones, 6 buildings |
| Create | `api/scenario_loader.py` | scan + parse `scenarios/*.json` |
| Modify | `api/server.py` | swap solver.scenarios → scenario_loader |
| Delete | `solver/scenarios.py` | replaced by JSON files |
| Modify | `tests/test_api.py` | update scenario name assertion |
| Modify | `frontend/scene.js` | add `resetGrid`, `clearBuildings`, `_buildGridLines` |
| Modify | `frontend/index.html` | dynamic scenario loading, remove hardcoded grid |
| Modify | `frontend/ui.js` | remove dead slider-era references |

---

## Task 1: `api/scenario_loader.py` + test

**Files:**
- Create: `api/scenario_loader.py`
- Modify: `tests/test_api.py` (add loader test)

- [ ] **Step 1: Write the failing test**

Add at the top of `tests/test_api.py` (after existing imports):

```python
from api.scenario_loader import load_all
```

Add these two tests at the end of `tests/test_api.py`:

```python
def test_load_all_returns_five_scenarios():
    scenarios = load_all()
    assert len(scenarios) == 5

def test_each_scenario_has_required_keys():
    for s in load_all():
        assert "name" in s
        assert "description" in s
        assert "grid" in s
        assert "drones" in s
        assert "buildings" in s
        assert {"rows", "cols", "alts"} == set(s["grid"].keys())
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_api.py::test_load_all_returns_five_scenarios tests/test_api.py::test_each_scenario_has_required_keys -v
```

Expected: `ImportError: cannot import name 'load_all' from 'api.scenario_loader'`

- [ ] **Step 3: Create `api/scenario_loader.py`**

```python
import json
import pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "scenarios"


def load_all():
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(SCENARIOS_DIR.glob("*.json"))
    ]
```

- [ ] **Step 4: Run tests — expect failure because `scenarios/` doesn't exist yet**

```
pytest tests/test_api.py::test_load_all_returns_five_scenarios -v
```

Expected: `FAIL` — `FileNotFoundError` or empty list (the folder doesn't exist yet — that's fine, the JSON files come in Task 2).

- [ ] **Step 5: Commit the loader (tests will pass after Task 2)**

```
git add api/scenario_loader.py tests/test_api.py
git commit -m "feat: add scenario_loader + loader tests"
```

---

## Task 2: Create the 5 JSON scenario files

**Files:**
- Create: `scenarios/micro_flat.json`
- Create: `scenarios/micro_3d.json`
- Create: `scenarios/medium_flat.json`
- Create: `scenarios/medium_city.json`
- Create: `scenarios/big_city.json`

For `alts == 1` grids, drone positions are `[row, col]`.
For `alts > 1` grids, drone positions are `[row, col, alt]`.

- [ ] **Step 1: Create `scenarios/micro_flat.json`**

```json
{
  "name": "micro_flat",
  "description": "4×4 grid, 3 drones — minimal 2D",
  "grid": { "rows": 4, "cols": 4, "alts": 1 },
  "drones": [
    { "id": 0, "start": [0, 0], "goal": [3, 3] },
    { "id": 1, "start": [3, 0], "goal": [0, 3] },
    { "id": 2, "start": [0, 3], "goal": [3, 0] }
  ],
  "buildings": [],
  "nofly": []
}
```

- [ ] **Step 2: Create `scenarios/micro_3d.json`**

```json
{
  "name": "micro_3d",
  "description": "4×4×3 grid, 4 drones — minimal 3D",
  "grid": { "rows": 4, "cols": 4, "alts": 3 },
  "drones": [
    { "id": 0, "start": [0, 0, 0], "goal": [3, 3, 2] },
    { "id": 1, "start": [3, 0, 0], "goal": [0, 3, 2] },
    { "id": 2, "start": [0, 3, 1], "goal": [3, 0, 1] },
    { "id": 3, "start": [3, 3, 0], "goal": [0, 0, 2] }
  ],
  "buildings": [
    { "row": 1, "col": 1, "height": 2 },
    { "row": 2, "col": 2, "height": 2 }
  ],
  "nofly": []
}
```

- [ ] **Step 3: Create `scenarios/medium_flat.json`**

```json
{
  "name": "medium_flat",
  "description": "6×8 grid, 5 drones — medium 2D",
  "grid": { "rows": 6, "cols": 8, "alts": 1 },
  "drones": [
    { "id": 0, "start": [0, 0], "goal": [5, 7] },
    { "id": 1, "start": [5, 0], "goal": [0, 7] },
    { "id": 2, "start": [0, 7], "goal": [5, 0] },
    { "id": 3, "start": [2, 0], "goal": [2, 7] },
    { "id": 4, "start": [0, 3], "goal": [5, 4] }
  ],
  "buildings": [],
  "nofly": []
}
```

- [ ] **Step 4: Create `scenarios/medium_city.json`**

```json
{
  "name": "medium_city",
  "description": "8×6×3 grid, 6 drones — medium 3D city",
  "grid": { "rows": 8, "cols": 6, "alts": 3 },
  "drones": [
    { "id": 0, "start": [0, 0, 0], "goal": [7, 5, 2] },
    { "id": 1, "start": [7, 0, 0], "goal": [0, 5, 2] },
    { "id": 2, "start": [0, 5, 1], "goal": [7, 0, 1] },
    { "id": 3, "start": [7, 5, 0], "goal": [0, 0, 2] },
    { "id": 4, "start": [3, 0, 0], "goal": [4, 5, 2] },
    { "id": 5, "start": [4, 5, 0], "goal": [3, 0, 2] }
  ],
  "buildings": [
    { "row": 2, "col": 2, "height": 2 },
    { "row": 5, "col": 3, "height": 2 },
    { "row": 3, "col": 4, "height": 1 }
  ],
  "nofly": []
}
```

- [ ] **Step 5: Create `scenarios/big_city.json`**

```json
{
  "name": "big_city",
  "description": "10×10×3 grid, 8 drones — full city 3D",
  "grid": { "rows": 10, "cols": 10, "alts": 3 },
  "drones": [
    { "id": 0, "start": [0, 0, 0], "goal": [9, 9, 2] },
    { "id": 1, "start": [9, 0, 0], "goal": [0, 9, 2] },
    { "id": 2, "start": [0, 9, 1], "goal": [9, 0, 1] },
    { "id": 3, "start": [9, 9, 0], "goal": [0, 0, 2] },
    { "id": 4, "start": [0, 4, 0], "goal": [9, 5, 2] },
    { "id": 5, "start": [9, 5, 0], "goal": [0, 4, 2] },
    { "id": 6, "start": [4, 0, 0], "goal": [5, 9, 1] },
    { "id": 7, "start": [5, 9, 0], "goal": [4, 0, 2] }
  ],
  "buildings": [
    { "row": 2, "col": 2, "height": 2 },
    { "row": 2, "col": 3, "height": 2 },
    { "row": 5, "col": 5, "height": 3 },
    { "row": 7, "col": 2, "height": 2 },
    { "row": 3, "col": 7, "height": 2 },
    { "row": 7, "col": 7, "height": 2 }
  ],
  "nofly": []
}
```

- [ ] **Step 6: Run loader tests — should pass now**

```
pytest tests/test_api.py::test_load_all_returns_five_scenarios tests/test_api.py::test_each_scenario_has_required_keys -v
```

Expected: both PASS

- [ ] **Step 7: Commit**

```
git add scenarios/
git commit -m "feat: add 5 JSON scenario files (4x4 to 10x10)"
```

---

## Task 3: Update `api/server.py` + `tests/test_api.py`, delete `solver/scenarios.py`

**Files:**
- Modify: `api/server.py`
- Modify: `tests/test_api.py`
- Delete: `solver/scenarios.py`

- [ ] **Step 1: Update `tests/test_api.py` — fix the scenario name assertion**

Find this line in `test_get_scenarios`:
```python
    assert any(s["name"] == "city_2d" for s in data)
```

Replace with:
```python
    assert any(s["name"] == "micro_flat" for s in data)
    assert len(data) == 5
```

- [ ] **Step 2: Run the existing test to confirm it now fails**

```
pytest tests/test_api.py::test_get_scenarios -v
```

Expected: FAIL — `city_2d` assertion fails (still using old server import)

- [ ] **Step 3: Replace `api/server.py`**

Full new content of `api/server.py`:

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver
from api.scenario_loader import load_all


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route("/scenarios", methods=["GET"])
    def scenarios():
        return jsonify(load_all())

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

- [ ] **Step 4: Delete `solver/scenarios.py`**

```
git rm solver/scenarios.py
```

- [ ] **Step 5: Run all tests**

```
pytest tests/ -v
```

Expected: all tests PASS (`test_get_scenarios` now finds `micro_flat`, `test_solve_*` unchanged)

- [ ] **Step 6: Commit**

```
git add api/server.py tests/test_api.py
git commit -m "feat: server loads scenarios from JSON files, remove solver/scenarios.py"
```

---

## Task 4: Update `frontend/scene.js`

**Files:**
- Modify: `frontend/scene.js`

Changes: remove hardcoded camera position from constructor, add `resetGrid(rows, cols, alts)`, `_buildGridLines(rows, cols)`, `clearBuildings()`, update `addBuildings` to track lights for cleanup.

- [ ] **Step 1: Replace `frontend/scene.js` with the full new version**

```javascript
export class CityScene {
  constructor(renderer) {
    this.renderer = renderer;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xd4e8f8);
    this.scene.fog = new THREE.FogExp2(0xd4e8f8, 0.007);

    this.camera = new THREE.PerspectiveCamera(
      55, window.innerWidth / window.innerHeight, 0.1, 500
    );

    this.controls = new THREE.OrbitControls(this.camera, renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;

    this._groundMesh    = null;
    this._gridLines     = null;
    this._buildingObjects = [];
    this._noFlyMeshes   = [];

    this._addLights();
  }

  _addLights() {
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dir = new THREE.DirectionalLight(0xfff0d0, 0.8);
    dir.position.set(20, 40, 20);
    this.scene.add(dir);
    const fill = new THREE.DirectionalLight(0xaac8e8, 0.25);
    fill.position.set(-10, 10, -10);
    this.scene.add(fill);
  }

  // Rebuild ground + grid for new dimensions and reposition camera.
  resetGrid(rows, cols, alts = 1) {
    if (this._groundMesh) { this.scene.remove(this._groundMesh); this._groundMesh = null; }
    if (this._gridLines)  { this.scene.remove(this._gridLines);  this._gridLines  = null; }

    const cx = cols / 2, cz = rows / 2;

    this._groundMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(cols + 1, rows + 1),
      new THREE.MeshPhongMaterial({ color: 0x304a62 })
    );
    this._groundMesh.rotation.x = -Math.PI / 2;
    this._groundMesh.position.set(cx, -0.01, cz);
    this.scene.add(this._groundMesh);

    this._gridLines = this._buildGridLines(rows, cols);
    this.scene.add(this._gridLines);

    const dist = Math.max(rows, cols) * 1.4 + alts * 1.5;
    this.camera.position.set(cx + dist * 0.5, dist * 0.7, cz + dist);
    this.controls.target.set(cx, 0, cz);
    this.controls.update();
  }

  // Custom line grid that works for non-square maps (rows ≠ cols).
  _buildGridLines(rows, cols) {
    const pts = [];
    for (let c = 0; c <= cols; c++) pts.push(c, 0, 0,  c, 0, rows);
    for (let r = 0; r <= rows; r++) pts.push(0, 0, r,  cols, 0, r);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    return new THREE.LineSegments(
      geo,
      new THREE.LineBasicMaterial({ color: 0x608098, transparent: true, opacity: 0.7 })
    );
  }

  clearBuildings() {
    for (const obj of this._buildingObjects) this.scene.remove(obj);
    this._buildingObjects = [];
  }

  addBuildings(buildings, cellSize = 1.0) {
    for (const b of buildings) {
      const h = b.height * cellSize * 1.5;
      const geo = new THREE.BoxGeometry(cellSize * 0.85, h, cellSize * 0.85);
      const mat = new THREE.MeshPhongMaterial({
        color: 0x9ab4ca, emissive: 0x000000, transparent: true, opacity: 0.95,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(b.col * cellSize, h / 2, b.row * cellSize);
      this.scene.add(mesh);

      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: 0x1e3850, transparent: true, opacity: 0.7 })
      );
      edges.position.copy(mesh.position);
      this.scene.add(edges);

      this._buildingObjects.push(mesh, edges);

      if (b.height >= 3) {
        const light = new THREE.PointLight(0xffd060, 0.4, 5);
        light.position.set(b.col * cellSize, h + 0.3, b.row * cellSize);
        this.scene.add(light);
        this._buildingObjects.push(light);
      }
    }
  }

  addNoFlyBox(minPos, maxPos, cellSize = 1.0) {
    const [r0, c0] = minPos, [r1, c1] = maxPos;
    const w = (c1 - c0 + 1) * cellSize;
    const d = (r1 - r0 + 1) * cellSize;
    const h = 8;
    const geo = new THREE.BoxGeometry(w, h, d);

    const mesh = new THREE.Mesh(geo,
      new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.15 }));
    mesh.position.set((c0 + c1) / 2 * cellSize, h / 2, (r0 + r1) / 2 * cellSize);
    this.scene.add(mesh);

    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo),
      new THREE.LineBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.8 }));
    edges.position.copy(mesh.position);
    this.scene.add(edges);

    this._noFlyMeshes.push(mesh, edges);
    return mesh;
  }

  clearNoFly() {
    for (const m of this._noFlyMeshes) this.scene.remove(m);
    this._noFlyMeshes = [];
  }

  update()  { this.controls.update(); }
  render()  { this.renderer.render(this.scene, this.camera); }

  onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }
}
```

- [ ] **Step 2: Commit**

```
git add frontend/scene.js
git commit -m "feat(scene): resetGrid, clearBuildings, non-square grid lines, dynamic camera"
```

---

## Task 5: Refactor `frontend/index.html` + `frontend/ui.js`

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/ui.js`

Removes: `ROWS/COLS/ALTS` constants, `BUILDINGS`, `PRESETS`, `randomDrones()`, drone count slider HTML+CSS. Adds: dynamic scenario fetch + `loadScenario()`.

- [ ] **Step 1: Update `frontend/ui.js`**

The only change is removing the `#btn-random` `onchange` scenario-selector handler that toggled the slider — that logic moves entirely to `index.html`. Replace the full file with:

```javascript
export class UIManager {
  constructor({ onSolve, onPlay, onPause, onReset, onStep, onAddNoFly, onClearNoFly }) {
    this._nofly = [];
    this._placingNoFly = false;
    this._btnNF = document.getElementById('btn-nofly');

    document.getElementById('btn-solve').onclick  = () => onSolve(this._nofly);
    document.getElementById('btn-play').onclick   = onPlay;
    document.getElementById('btn-pause').onclick  = onPause;
    document.getElementById('btn-reset').onclick  = onReset;
    document.getElementById('btn-step').onclick   = onStep;

    this._btnNF.onclick = () => {
      this._placingNoFly = !this._placingNoFly;
      this._syncBtn();
    };

    document.getElementById('btn-clear-nofly').onclick = () => {
      this._nofly = [];
      this._placingNoFly = false;
      this._syncBtn();
      onClearNoFly();
    };

    this._onAddNoFly = onAddNoFly;
  }

  _syncBtn() {
    const on = this._placingNoFly;
    this._btnNF.classList.toggle('is-active', on);
    this._btnNF.textContent = on ? '🚫 Click grid…' : '🚫 No-Fly';
  }

  isPlacingNoFly() { return this._placingNoFly; }

  addNoFlyFromClick(row, col) {
    const nf = { min: [row, col], max: [row, col] };
    this._nofly.push(nf);
    this._onAddNoFly(nf);
  }

  getNoFly() { return this._nofly; }

  updateFrame(frame, maxFrame) {
    document.getElementById('h-frame').textContent = `${frame}/${maxFrame}`;
  }
}
```

Note: `btn-random` is renamed to `btn-solve` in both JS and HTML.

- [ ] **Step 2: Replace `frontend/index.html`**

Full new file — removes slider CSS, slider HTML, hardcoded constants and presets, adds dynamic init:

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>MAPF — City 3D</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Barlow:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --panel-bg:    rgba(255, 255, 255, 0.96);
    --border-base: rgba(15, 23, 42, 0.1);
    --border-lit:  rgba(37, 99, 235, 0.4);
    --text-dim:    #94a3b8;
    --text-muted:  #64748b;
    --text-base:   #334155;
    --text-strong: #0f172a;
    --accent:      #2563eb;
    --accent-dim:  rgba(37, 99, 235, 0.07);
    --danger:      #dc2626;
    --danger-dim:  rgba(220, 38, 38, 0.08);
    --warn:        #ea580c;
    --warn-dim:    rgba(234, 88, 12, 0.08);
    --shadow-panel: 0 2px 12px rgba(0,0,0,0.1), 0 1px 4px rgba(0,0,0,0.06);
    --shadow-bar:   0 6px 28px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #d4e8f8; overflow: hidden; }

  /* ── HUD Panel ───────────────────────────────────────────────── */
  #hud {
    position: fixed;
    top: 20px; left: 20px;
    z-index: 10;
    width: 214px;
    background: var(--panel-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-base);
    border-top: 2.5px solid var(--accent);
    border-radius: 10px;
    padding: 14px 16px 16px;
    pointer-events: none;
    box-shadow: var(--shadow-panel);
  }

  .hud-header {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-base);
  }

  .hud-badge {
    font-family: 'Audiowide', sans-serif;
    font-size: 8.5px;
    letter-spacing: 0.05em;
    color: white;
    background: var(--accent);
    border-radius: 3px;
    padding: 2px 8px 3px;
  }

  .hud-title {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .hud-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 3px 0;
  }

  .hud-lbl {
    font-family: 'Barlow', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--text-dim);
  }

  #hud .val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text-strong);
    letter-spacing: 0.01em;
  }

  .hud-scenario {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--border-base);
    pointer-events: all;
  }

  .hud-scenario-lbl {
    font-family: 'Barlow', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-dim);
    display: block;
    margin-bottom: 6px;
  }

  #sel-scenario {
    width: 100%;
    background: #f8fafc;
    color: var(--text-strong);
    border: 1px solid var(--border-base);
    border-radius: 6px;
    padding: 6px 26px 6px 9px;
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5'%3E%3Cpath d='M0 0l4 5 4-5z' fill='%232563eb' fill-opacity='.5'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 9px center;
    transition: border-color 0.18s, box-shadow 0.18s;
    outline: none;
  }

  #sel-scenario:hover, #sel-scenario:focus {
    border-color: var(--border-lit);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
    background-color: white;
  }

  #sel-scenario option {
    background: white;
    color: var(--text-strong);
  }

  .solving {
    animation: solving-pulse 1.1s ease-in-out infinite;
    color: var(--accent) !important;
  }
  @keyframes solving-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
  }

  /* ── Controls Bar ────────────────────────────────────────────── */
  #controls {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    display: flex;
    align-items: center;
    background: var(--panel-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-base);
    border-radius: 14px;
    padding: 9px 14px;
    box-shadow: var(--shadow-bar);
  }

  .ctrl-divider {
    width: 1px;
    height: 26px;
    background: var(--border-base);
    margin: 0 12px;
    flex-shrink: 0;
  }

  /* ── Playback group — segmented ──────────────────────────────── */
  .ctrl-playback {
    display: flex;
    gap: 0;
    background: #f1f5f9;
    border: 1px solid var(--border-base);
    border-radius: 8px;
    overflow: hidden;
  }

  .ctrl-playback button {
    padding: 6px 12px;
    background: transparent;
    border: none;
    border-right: 1px solid var(--border-base);
    border-radius: 0;
    color: var(--text-base);
    font-family: 'Barlow', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
    cursor: pointer;
    transition: background 0.14s, color 0.14s;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
    user-select: none;
  }

  .ctrl-playback button:last-child { border-right: none; }

  .ctrl-playback button:hover {
    background: white;
    color: var(--accent);
  }

  .ctrl-playback button:active {
    background: var(--accent-dim);
    transform: scale(0.97);
  }

  /* ── Actions group ───────────────────────────────────────────── */
  .ctrl-actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  button {
    position: relative;
    background: white;
    border: 1px solid var(--border-base);
    color: var(--text-base);
    border-radius: 8px;
    cursor: pointer;
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.04em;
    transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s, transform 0.08s;
    padding: 7px 14px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    user-select: none;
  }

  button:hover {
    background: var(--accent-dim);
    border-color: rgba(37, 99, 235, 0.35);
    color: var(--accent);
    box-shadow: 0 1px 6px rgba(37, 99, 235, 0.1);
  }

  button:active { transform: scale(0.96); }

  #btn-solve {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    box-shadow: 0 1px 6px rgba(37, 99, 235, 0.28);
  }

  #btn-solve:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
    color: white;
    box-shadow: 0 2px 10px rgba(37, 99, 235, 0.38);
  }

  #btn-nofly {
    border-color: rgba(234, 88, 12, 0.32);
    color: var(--warn);
    background: var(--warn-dim);
  }

  #btn-nofly:hover {
    background: rgba(234, 88, 12, 0.13);
    border-color: var(--warn);
    color: #c2410c;
    box-shadow: 0 1px 6px rgba(234, 88, 12, 0.15);
  }

  #btn-nofly.is-active {
    background: var(--danger-dim);
    border-color: var(--danger);
    color: var(--danger);
    box-shadow: 0 1px 8px rgba(220, 38, 38, 0.18);
  }

  #btn-clear-nofly {
    padding: 7px 10px;
    min-width: 36px;
    justify-content: center;
    background: #f8fafc;
    border-color: var(--border-base);
    color: var(--text-muted);
    font-size: 15px;
    font-weight: 400;
  }

  #btn-clear-nofly:hover {
    border-color: rgba(220, 38, 38, 0.4);
    color: var(--danger);
    background: var(--danger-dim);
    box-shadow: 0 1px 4px rgba(220, 38, 38, 0.1);
  }
</style>
</head>
<body>

<div id="hud">
  <div class="hud-header">
    <span class="hud-badge">MAPF</span>
    <span class="hud-title">Drone Coord.</span>
  </div>
  <div class="hud-row">
    <span class="hud-lbl">Status</span>
    <span class="val" id="h-status">—</span>
  </div>
  <div class="hud-row">
    <span class="hud-lbl">Makespan</span>
    <span class="val" id="h-makespan">—</span>
  </div>
  <div class="hud-row">
    <span class="hud-lbl">Solve</span>
    <span class="val" id="h-time">—</span>
  </div>
  <div class="hud-row">
    <span class="hud-lbl">Conflicts</span>
    <span class="val" id="h-conflicts">—</span>
  </div>
  <div class="hud-row">
    <span class="hud-lbl">Frame</span>
    <span class="val" id="h-frame">—</span>
  </div>
  <div class="hud-scenario">
    <span class="hud-scenario-lbl">Scenario</span>
    <select id="sel-scenario"></select>
  </div>
</div>

<div id="controls">
  <div class="ctrl-playback">
    <button id="btn-play">&#9654; Play</button>
    <button id="btn-pause">&#9646;&#9646; Pause</button>
    <button id="btn-step">&#x23ED; Step</button>
    <button id="btn-reset">&#x21BA; Reset</button>
  </div>
  <div class="ctrl-divider"></div>
  <div class="ctrl-actions">
    <button id="btn-solve">&#x26A1; Solve</button>
    <button id="btn-nofly">&#x1F6AB; No-Fly</button>
    <button id="btn-clear-nofly" title="Clear no-fly zones">&#x2715;</button>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script type="module">
import { CityScene }    from './scene.js';
import { DroneManager } from './drones.js';
import { UIManager }    from './ui.js';
import { fetchScenarios, fetchSolve } from './api.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const cityScene = new CityScene(renderer);
let droneManager = null, solution = null, currentScenario = null;
let playing = false, frame = 0, lastTick = 0;
const SPEED_MS = 380;

// ── UIManager ─────────────────────────────────────────────────────────────────
const ui = new UIManager({
  onSolve:      (nofly) => { if (currentScenario) solve(currentScenario, nofly); },
  onPlay:       () => { if (solution) playing = true; },
  onPause:      () => { playing = false; },
  onReset:      () => {
    playing = false; frame = 0;
    if (droneManager && solution) {
      droneManager.resetForReplay(solution.paths);
      ui.updateFrame(0, solution.makespan);
    }
  },
  onStep:       () => {
    if (solution && droneManager && frame < solution.makespan) {
      frame++;
      droneManager.updateFrame(solution.paths, frame);
      ui.updateFrame(frame, solution.makespan);
    }
  },
  onAddNoFly:   (nf) => cityScene.addNoFlyBox(nf.min, nf.max),
  onClearNoFly: ()   => cityScene.clearNoFly(),
});

// ── Scenario loading ──────────────────────────────────────────────────────────
async function init() {
  const scenarios = await fetchScenarios();
  const select = document.getElementById('sel-scenario');
  for (const s of scenarios) {
    const opt = document.createElement('option');
    opt.value = s.name;
    opt.textContent = s.description;
    select.appendChild(opt);
  }
  select.onchange = () => {
    const s = scenarios.find(s => s.name === select.value);
    if (s) loadScenario(s);
  };
  if (scenarios.length > 0) loadScenario(scenarios[0]);
}

function loadScenario(scenario) {
  currentScenario = scenario;
  const { rows, cols, alts } = scenario.grid;
  cityScene.resetGrid(rows, cols, alts);
  cityScene.clearBuildings();
  cityScene.addBuildings(scenario.buildings || []);
  solve(scenario);
}

// ── Solve ─────────────────────────────────────────────────────────────────────
async function solve(scenario, nofly = []) {
  playing = false; frame = 0; solution = null;

  const statusEl = document.getElementById('h-status');
  statusEl.textContent = 'Solving…';
  statusEl.classList.add('solving');
  ['h-makespan', 'h-time', 'h-conflicts', 'h-frame'].forEach(id => {
    document.getElementById(id).textContent = '—';
  });

  if (droneManager) { droneManager.dispose(cityScene.scene); droneManager = null; }

  solution = await fetchSolve({
    grid:      scenario.grid,
    drones:    scenario.drones,
    buildings: scenario.buildings || [],
    nofly,
    time_limit_s: 30,
  });

  statusEl.classList.remove('solving');
  statusEl.textContent                               = solution.status;
  document.getElementById('h-makespan').textContent  = solution.makespan;
  document.getElementById('h-time').textContent      = solution.solve_time_ms + 'ms';
  document.getElementById('h-conflicts').textContent = solution.conflicts_avoided;

  if (solution.status === 'infeasible') return;

  droneManager = new DroneManager(scenario.drones, cityScene.scene);
  droneManager.updateFrame(solution.paths, 0, true);
  ui.updateFrame(0, solution.makespan);
}

// ── No-fly Raycaster ──────────────────────────────────────────────────────────
const raycaster   = new THREE.Raycaster();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

renderer.domElement.addEventListener('click', (e) => {
  if (!ui.isPlacingNoFly() || !currentScenario) return;
  const { rows, cols } = currentScenario.grid;
  const mouse = new THREE.Vector2(
    (e.clientX / window.innerWidth) * 2 - 1,
    -(e.clientY / window.innerHeight) * 2 + 1
  );
  raycaster.setFromCamera(mouse, cityScene.camera);
  const pt = new THREE.Vector3();
  if (raycaster.ray.intersectPlane(groundPlane, pt)) {
    const row = Math.floor(pt.z), col = Math.floor(pt.x);
    if (row >= 0 && col >= 0 && row < rows && col < cols)
      ui.addNoFlyFromClick(row, col);
  }
});

// ── Render loop ───────────────────────────────────────────────────────────────
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
window.addEventListener('resize', () => cityScene.onResize());

init();
</script>
</body>
</html>
```

- [ ] **Step 3: Run all backend tests one final time**

```
pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 4: Manual smoke test**

Start the server: `python -m api.server` (or `flask run`)

Open `frontend/index.html` in a browser (via a local HTTP server or Live Server). Verify:
- Dropdown is populated with 5 scenario names from the API
- Selecting `micro_flat` shows a 4×4 grid, camera positioned above it
- Selecting `big_city` shows a 10×10 grid, camera pulls back accordingly
- Selecting `medium_flat` (6×8) or `medium_city` (8×6) shows a visibly non-square grid
- Solve runs and drones animate
- No-fly zone placement still works

- [ ] **Step 5: Final commit**

```
git add frontend/index.html frontend/ui.js
git commit -m "feat(frontend): dynamic scenario loading, remove hardcoded grid + presets"
```
