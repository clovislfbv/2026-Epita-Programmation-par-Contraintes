# Design Spec — Scenarios Refactor + Variable Map Sizes
**Date:** 2026-05-15
**Author:** Paul Witkowski

---

## 1. Goals

1. Scenarios can have maps of any shape (rows, cols, alts all independent).
2. Scenarios live in their own `scenarios/` folder as JSON files — no code change needed to add one.
3. The backend loads them dynamically; the frontend fetches them from the backend.
4. Replace all current scenarios (backend `small_2d`/`city_2d`/`city_3d`, frontend presets `cross`/`altitude`/`random`) with 5 new ones.
5. Light cleanup of frontend boilerplate alongside the feature work.

---

## 2. Scenario Files

### Location
```
scenarios/               ← new folder at repo root
  micro_flat.json
  micro_3d.json
  medium_flat.json
  medium_city.json
  big_city.json
```

### JSON Schema
```json
{
  "name": "medium_flat",
  "description": "6×8 grid, 5 drones — medium 2D",
  "grid": { "rows": 6, "cols": 8, "alts": 1 },
  "drones": [
    { "id": 0, "start": [0, 0], "goal": [5, 7] }
  ],
  "buildings": [],
  "nofly": []
}
```

- `alts == 1` → drone positions are `[row, col]` (2D)
- `alts > 1`  → drone positions are `[row, col, alt]` (3D)
- `buildings` entries: `{ "row": int, "col": int, "height": int }`
- `nofly` entries: `{ "min": [...], "max": [...] }`

### The 5 Scenarios

| File | Grid | Drones | Buildings | Notes |
|------|------|--------|-----------|-------|
| `micro_flat.json` | 4×4×1 | 3 | 0 | minimal 2D |
| `micro_3d.json` | 4×4×3 | 4 | 2 | minimal 3D |
| `medium_flat.json` | 6×8×1 | 5 | 0 | non-square 2D |
| `medium_city.json` | 8×6×3 | 6 | 3 | non-square 3D |
| `big_city.json` | 10×10×3 | 8 | 6 | full city 3D |

Non-square scenarios (`medium_flat`, `medium_city`) explicitly exercise rows ≠ cols.

---

## 3. Backend Changes

### Deleted
- `solver/scenarios.py` — replaced by JSON files + loader

### New: `api/scenario_loader.py`
```python
import json, pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "scenarios"

def load_all():
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(SCENARIOS_DIR.glob("*.json"))
    ]
```

### Updated: `api/server.py`
- `GET /scenarios` returns `load_all()` — full scenario data including grid, drones, buildings
- `POST /solve` unchanged — already accepts `grid`, `drones`, `buildings`, `nofly`
- Remove import of `solver.scenarios`

### Updated: Tests
- `tests/test_api.py`: replace `get_scenario`/`list_scenarios` calls with direct JSON fixture data
- `tests/test_mapf.py`: same — use inline dicts instead of scenario helpers

---

## 4. Frontend Changes

### Removed
- Hardcoded constants `ROWS`, `COLS`, `ALTS`
- `BUILDINGS` array and `blocked` set
- `PRESETS` object (`cross`, `altitude`)
- `randomDrones()` function
- Drone count slider (`#n-drones`, `#n-label`, `#slider-wrap`)
- Hardcoded `<option>` elements in `#sel-scenario`

### New flow
1. **On load**: `fetchScenarios()` → populate `<select id="sel-scenario">` with `name`/`description` from API
2. **On scenario change**: `loadScenario(scenario)` — rebuilds scene, launches solve
3. **Solve**: passes `scenario.grid`, `scenario.drones`, `scenario.buildings` directly to `POST /solve`

### `CityScene` additions (`scene.js`)
- `resetGrid(rows, cols)` — removes old ground mesh + grid helper, creates new ones at correct size
- `clearBuildings()` — removes building meshes from previous scenario
- Camera reposition formula on scenario load:
  ```js
  const dist = Math.max(rows, cols) * 1.4 + alts * 1.5;
  camera.position.set(cols/2 + dist*0.5, dist*0.7, rows/2 + dist);
  controls.target.set(cols/2, 0, rows/2);
  ```
  Always centers on grid, always clears tallest buildings regardless of `alts`.

### Cleanup (alongside feature work)
- Remove commented-out dead code in `index.html`
- `UIManager` (`ui.js`): remove slider-related methods, tighten constructor
- `scene.js`: remove hardcoded camera/target values from constructor (set by `loadScenario` instead)

---

## 5. API Contract (unchanged for `/solve`)

`POST /solve` body already matches the scenario JSON shape — no mapping needed:
```json
{
  "grid": { "rows": 8, "cols": 6, "alts": 3 },
  "drones": [...],
  "buildings": [...],
  "nofly": [],
  "time_limit_s": 30
}
```

`GET /scenarios` returns an array of full scenario objects.

---

## 6. Out of Scope

- Random drone generator (removed, not replaced)
- Scenario editor UI
- Hot-reload of scenario files without restarting the server
