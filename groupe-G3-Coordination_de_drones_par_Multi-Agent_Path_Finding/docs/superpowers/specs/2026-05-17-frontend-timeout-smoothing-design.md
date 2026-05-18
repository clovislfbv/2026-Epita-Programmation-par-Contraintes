# Design — Timeout input & Animation Smoothing

**Date:** 2026-05-17  
**Scope:** `frontend/index.html`, `frontend/drones.js`, `frontend/ui.js`

---

## 1. Timeout Input

### Problem
`time_limit_s` is hardcoded to `30` in `solve()` (`index.html:476`). Users cannot adjust it without editing the source.

### Solution
Add a `<input type="number">` field in `.ctrl-actions`, between `#sel-method` and `#btn-solve`.

**HTML addition:**
```html
<label class="ctrl-label">⏱</label>
<input type="number" id="inp-timeout" min="1" max="300" value="30" title="Timeout (s)">
```

**`solve()` change:**
```js
// Before
time_limit_s: 30,

// After
time_limit_s: Number(document.getElementById('inp-timeout').value),
```

**Styling:** same dark background / border as `#sel-method`. Width ~70px to fit 3 digits comfortably.

---

## 2. Animation Smoothing

### Problem
The render loop (`loop()` in `index.html`) advances drones one discrete step every `SPEED_MS = 380ms`, producing jerky movement.

### Solution
Two additions:
- A toggle button `#btn-smooth` to enable/disable interpolation
- A range slider `#sld-speed` to control animation speed (ms per step), replacing the hardcoded `SPEED_MS`

### HTML additions (in `.ctrl-playback`, after Reset)
```html
<div class="ctrl-divider"></div>
<button id="btn-smooth">〜 Smooth</button>
<input type="range" id="sld-speed" min="80" max="1500" value="380" title="Vitesse (ms/step)">
```

### DroneManager — new method (`drones.js`)
```js
updateFrameLerp(paths, frame, t) {
  // t ∈ [0, 1]: interpolates each drone between paths[frame] and paths[frame+1]
  // Falls back to updateFrame(paths, frame) when frame+1 is out of bounds
}
```
Linear interpolation: `pos = A + (B - A) * t` applied to each axis independently via `_toWorld()`.

### Render loop logic (`index.html`)

State variables added:
```js
let smoothing = false;
// speedMs = Number(sld-speed.value), read each frame
```

`loop(ts)` becomes:

```
if playing && solution && droneManager:
  speedMs = Number(sld-speed.value)

  if smooth OFF:
    if ts - lastTick > speedMs:
      lastTick = ts
      advance frame, call updateFrame(paths, frame)

  if smooth ON:
    t = (ts - lastFrameTime) / speedMs   // [0, 1+]
    call updateFrameLerp(paths, frame, clamp(t, 0, 1))
    if t >= 1:
      lastFrameTime = ts
      frame++
      if frame >= makespan: playing = false
```

`lastFrameTime` replaces `lastTick` for smooth mode.

### Button visual state
`#btn-smooth` toggles class `.is-active` (same pattern as `#btn-nofly`).

---

## Files Changed

| File | Change |
|---|---|
| `frontend/index.html` | Add timeout input, smoothing button + slider, update `solve()` and `loop()` |
| `frontend/drones.js` | Add `updateFrameLerp()` method to `DroneManager` |
| `frontend/ui.js` | No change required (controls are read directly in `index.html`) |

---

## Out of Scope
- Persisting timeout/speed preferences across page reload
- Easing functions (cubic, ease-in-out) — linear lerp only
- Speed label display (raw ms value visible on hover via `title` attribute)
