# Frontend — Timeout Input & Animation Smoothing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable timeout input next to the algo selector, and a smooth-lerp animation mode with a speed slider in the playback bar.

**Architecture:** `DroneManager` gains `updateFrameLerp()` for sub-frame position interpolation. `index.html` gains the HTML controls and updated `solve()` / `loop()` logic. No new files needed.

**Tech Stack:** Vanilla JS, Three.js (already in use), HTML/CSS in `index.html`.

---

## File Map

| File | Change |
|---|---|
| `frontend/drones.js` | Add `updateFrameLerp(paths, frame, alpha)` method |
| `frontend/index.html` | CSS for new controls; HTML for timeout input + smoothing button + slider; update `solve()` and `loop()` |

---

## Task 1 — Add `updateFrameLerp()` to `DroneManager`

**Files:**
- Modify: `frontend/drones.js` — add method after `updateFrame()`

- [ ] **Step 1: Add the method**

In `frontend/drones.js`, after the closing `}` of `updateFrame()` (line 115) and before `_flash()`, insert:

```js
  updateFrameLerp(paths, frame, alpha) {
    for (const d of this.drones) {
      const path = paths[String(d.id)];
      if (!path) continue;
      const wA = this._toWorld(path[Math.min(frame,     path.length - 1)]);
      const wB = this._toWorld(path[Math.min(frame + 1, path.length - 1)]);
      const world = new THREE.Vector3(
        wA.x + (wB.x - wA.x) * alpha,
        wA.y + (wB.y - wA.y) * alpha,
        wA.z + (wB.z - wA.z) * alpha,
      );
      d.mesh.position.copy(world);
      d.baseY = world.y;
    }
    for (let i = 0; i < this.drones.length; i++)
      for (let j = i + 1; j < this.drones.length; j++)
        if (this.drones[i].mesh.position.distanceTo(this.drones[j].mesh.position) < 1.2 * CELL)
          this._flash(this.drones[i], this.drones[j]);
  }
```

> Note: trail is intentionally not updated during sub-frame lerp calls (called ~60fps) to avoid trail overflow. The trail stays at its last `updateFrame` snapshot, which is fine visually.

- [ ] **Step 2: Verify the file is valid JS**

Open `frontend/drones.js` in your editor and confirm:
- `updateFrameLerp` appears between `updateFrame` and `_flash`
- `DroneManager` class closes with a single `}` at the end
- No syntax errors (the IDE should show none)

- [ ] **Step 3: Commit**

```bash
git add frontend/drones.js
git commit -m "feat(frontend): add DroneManager.updateFrameLerp for smooth animation"
```

---

## Task 2 — Timeout Input: HTML, CSS, and `solve()` wiring

**Files:**
- Modify: `frontend/index.html`

### Step-by-step

- [ ] **Step 1: Add CSS for `#inp-timeout` and `.ctrl-label`**

In `<style>`, after the `select:hover` rule (around line 323), add:

```css
  .ctrl-label {
    font-size: 14px;
    color: var(--text-muted);
  }

  #inp-timeout {
    width: 68px;
    padding: 7px 10px;
    background: #0f172a;
    border: 1px solid #334155;
    color: #94a3b8;
    border-radius: 6px;
    font-size: 13px;
    font-family: 'Barlow', sans-serif;
    font-weight: 600;
    text-align: center;
  }
  #inp-timeout:hover { border-color: #3b82f6; color: #fff; }
  #inp-timeout:focus { outline: none; border-color: #3b82f6; color: #fff; }
```

- [ ] **Step 2: Add the input HTML in `.ctrl-actions`**

Find the `.ctrl-actions` div (around line 375):
```html
  <div class="ctrl-actions">
    <select id="sel-method" title="Solving method">
      ...
    </select>
    <button id="btn-solve">&#x26A1; Solve</button>
```

Insert between `</select>` and `<button id="btn-solve">`:
```html
    <label class="ctrl-label" title="Timeout solver (secondes)">⏱</label>
    <input type="number" id="inp-timeout" min="1" max="300" value="30" title="Timeout (s)">
```

Result:
```html
  <div class="ctrl-actions">
    <select id="sel-method" title="Solving method">
      <option value="cpsat">CP-SAT optimal</option>
      <option value="cbs">CBS (optimal)</option>
      <option value="ecbs">ECBS (rapide ×1.3)</option>
      <option value="od_astar">A* OD (optimal, N≤5)</option>
    </select>
    <label class="ctrl-label" title="Timeout solver (secondes)">⏱</label>
    <input type="number" id="inp-timeout" min="1" max="300" value="30" title="Timeout (s)">
    <button id="btn-solve">&#x26A1; Solve</button>
    <button id="btn-nofly">&#x1F6AB; No-Fly</button>
    <button id="btn-clear-nofly" title="Clear no-fly zones">&#x2715;</button>
  </div>
```

- [ ] **Step 3: Wire `solve()` to read the input**

In `solve()` (around line 470), find:
```js
    time_limit_s: 30,
```

Replace with:
```js
    time_limit_s: Number(document.getElementById('inp-timeout').value),
```

- [ ] **Step 4: Manual smoke test**

Open the frontend in a browser. Verify:
- A small numeric input appears between the algo selector and the Solve button
- Default value is `30`
- Changing it to `5` and clicking Solve shows a faster timeout on a heavy scenario (e.g., scenario 11 mega with CP-SAT)
- The HUD "Solve" time reflects the shorter run

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): configurable timeout input in solver controls"
```

---

## Task 3 — Smoothing Toggle + Speed Slider: HTML, CSS, and `loop()` wiring

**Files:**
- Modify: `frontend/index.html`

### Step-by-step

- [ ] **Step 1: Add CSS for `#btn-smooth` and `#sld-speed`**

In `<style>`, after the `#inp-timeout` rules added in Task 2, add:

```css
  #btn-smooth.is-active {
    background: var(--accent-dim);
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 1px 8px rgba(37, 99, 235, 0.18);
  }

  #sld-speed {
    width: 90px;
    accent-color: var(--accent);
    cursor: pointer;
  }
```

- [ ] **Step 2: Add HTML in `.ctrl-playback`**

Find the `.ctrl-playback` div (around line 368):
```html
  <div class="ctrl-playback">
    <button id="btn-play">&#9654; Play</button>
    <button id="btn-pause">&#9646;&#9646; Pause</button>
    <button id="btn-step">&#x23ED; Step</button>
    <button id="btn-reset">&#x21BA; Reset</button>
  </div>
```

Replace with:
```html
  <div class="ctrl-playback">
    <button id="btn-play">&#9654; Play</button>
    <button id="btn-pause">&#9646;&#9646; Pause</button>
    <button id="btn-step">&#x23ED; Step</button>
    <button id="btn-reset">&#x21BA; Reset</button>
    <div class="ctrl-divider"></div>
    <button id="btn-smooth" title="Animation lissée (lerp)">〜 Smooth</button>
    <input type="range" id="sld-speed" min="80" max="1500" value="380" title="Vitesse (ms/step)">
  </div>
```

- [ ] **Step 3: Add state variables**

In `index.html`, in the script block, find:
```js
let playing = false, frame = 0, lastTick = 0;
const SPEED_MS = 380;
```

Replace with:
```js
let playing = false, frame = 0, lastTick = 0, lastFrameTime = 0;
let smoothing = false;
```

> `SPEED_MS` is removed — speed is now read live from `#sld-speed`.

- [ ] **Step 4: Wire the smooth toggle button**

In the `UIManager` callbacks block (around line 407), after the existing callbacks and before the closing `}`  of the `new UIManager({...})` call, there is no existing handler for btn-smooth — add it directly after the `new UIManager` block:

```js
document.getElementById('btn-smooth').onclick = () => {
  smoothing = !smoothing;
  lastFrameTime = performance.now();
  document.getElementById('btn-smooth').classList.toggle('is-active', smoothing);
};
```

- [ ] **Step 5: Update `loop()` to use smooth mode and dynamic speed**

Find the `loop()` function (around line 515):
```js
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
```

Replace with:
```js
function loop(ts) {
  requestAnimationFrame(loop);
  if (playing && solution && droneManager) {
    const speedMs = Number(document.getElementById('sld-speed').value);
    if (!smoothing) {
      if (ts - lastTick > speedMs) {
        lastTick = ts;
        if (frame < solution.makespan) {
          frame++;
          droneManager.updateFrame(solution.paths, frame);
          ui.updateFrame(frame, solution.makespan);
        } else { playing = false; }
      }
    } else {
      const alpha = Math.min((ts - lastFrameTime) / speedMs, 1);
      droneManager.updateFrameLerp(solution.paths, frame, alpha);
      if (alpha >= 1) {
        lastFrameTime = ts;
        if (frame < solution.makespan) {
          frame++;
          ui.updateFrame(frame, solution.makespan);
        } else { playing = false; }
      }
    }
  }
  droneManager?.animateTrails();
  cityScene.update();
  cityScene.render();
}
```

- [ ] **Step 6: Manual smoke test — discrete mode**

Open the frontend. Without activating Smooth:
- Play a scenario — drones move in discrete jumps as before
- Move the speed slider left (fast) → drones advance more quickly
- Move the slider right (slow) → drones advance more slowly

- [ ] **Step 7: Manual smoke test — smooth mode**

- Click `〜 Smooth` → button highlights blue (`.is-active`)
- Click Play → drones glide continuously between steps
- Adjust speed slider → interpolation duration changes
- Click Smooth again → button unhighlights, reverts to discrete mode

- [ ] **Step 8: Edge cases**

- Toggle smooth ON mid-playback → no crash, position continues smoothly
- Reach end of paths in smooth mode → `playing` becomes `false`, drones stop at last position
- Step button while smooth is ON → should still work (Step calls `updateFrame` directly, not the loop)

- [ ] **Step 9: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): smooth animation toggle with speed slider"
```

---

## Task 4 — Final Integration Check

- [ ] **Step 1: Test timeout + smoothing together**

- Set timeout to `5s`, select CP-SAT, run a heavy scenario → times out in ~5s
- Enable smooth + adjust speed → animation plays smoothly
- Disable smooth → reverts to discrete, speed slider still controls SPEED_MS

- [ ] **Step 2: Check browser console**

Open DevTools → Console. Confirm zero errors during normal usage (solve, play, toggle smooth, adjust speed, step, reset).

- [ ] **Step 3: Final commit if any stray fixes**

```bash
git add frontend/index.html frontend/drones.js
git commit -m "fix(frontend): cleanup after timeout + smoothing integration"
```
