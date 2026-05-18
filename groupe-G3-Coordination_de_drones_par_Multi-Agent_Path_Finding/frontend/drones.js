const COLORS = [
  0x3b82f6, 0xef4444, 0x22c55e, 0xf59e0b, 0xa855f7,
  0x06b6d4, 0xec4899, 0x84cc16, 0xfb923c, 0xe11d48,
  0x8b5cf6, 0x0ea5e9, 0x10b981, 0xf97316, 0x6366f1,
];
const CELL      = 1.0;
const TRAIL_LEN = 60;

export class DroneManager {
  constructor(droneConfigs, scene) {
    this.scene  = scene;
    this.drones = [];

    for (let i = 0; i < droneConfigs.length; i++) {
      const col = COLORS[i % COLORS.length];
      const d   = droneConfigs[i];

      // Body + point-light glow
      const geo  = new THREE.SphereGeometry(0.22, 14, 14);
      const mat  = new THREE.MeshPhongMaterial({ color: col, emissive: col, emissiveIntensity: 0.7 });
      const mesh = new THREE.Mesh(geo, mat);
      const light = new THREE.PointLight(col, 1.8, 4.5);
      mesh.add(light);
      scene.add(mesh);

      // Trail
      const buf      = new Float32Array(TRAIL_LEN * 3);
      const trailGeo = new THREE.BufferGeometry();
      trailGeo.setAttribute('position', new THREE.BufferAttribute(buf, 3));
      trailGeo.setDrawRange(0, 0);
      const trail = new THREE.Line(trailGeo,
        new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.5 }));
      scene.add(trail);

      // Start — torus ring at actual start altitude
      const startY = this._toWorld(d.start).y;
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.32, 0.06, 8, 24),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.55 })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set((d.start[1] + 0.5) * CELL, startY, (d.start[0] + 0.5) * CELL);
      scene.add(ring);

      // Goal — pillar up to goal altitude + ring + star at that height
      const goalY = this._toWorld(d.goal).y;
      const pillarH = Math.max(goalY, 0.1);
      const pillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.05, 0.05, pillarH, 8),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.65 })
      );
      pillar.position.set((d.goal[1] + 0.5) * CELL, pillarH / 2, (d.goal[0] + 0.5) * CELL);
      scene.add(pillar);

      const beacon = new THREE.PointLight(col, 0.9, 3.5);
      beacon.position.set((d.goal[1] + 0.5) * CELL, goalY, (d.goal[0] + 0.5) * CELL);
      scene.add(beacon);

      const goalRing = new THREE.Mesh(
        new THREE.TorusGeometry(0.32, 0.06, 8, 24),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.8 })
      );
      goalRing.rotation.x = -Math.PI / 2;
      goalRing.position.set((d.goal[1] + 0.5) * CELL, goalY, (d.goal[0] + 0.5) * CELL);
      scene.add(goalRing);

      // Star marker just above the goal ring
      const star = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.18),
        new THREE.MeshBasicMaterial({ color: col })
      );
      star.position.set((d.goal[1] + 0.5) * CELL, goalY + 0.35, (d.goal[0] + 0.5) * CELL);
      scene.add(star);

      this.drones.push({
        id: d.id, mesh, trail, trailPts: [], baseY: null,
        ring, pillar, beacon, goalRing, star, col,
      });
    }
  }

  _toWorld(pos) {
    return new THREE.Vector3(
      (pos[1] + 0.5) * CELL,
      (pos[2] ?? 0) * CELL * 1.5 + 0.4,
      (pos[0] + 0.5) * CELL
    );
  }

  updateFrame(paths, t, skipTrail = false) {
    for (const d of this.drones) {
      const path = paths[String(d.id)];
      if (!path) continue;
      const world = this._toWorld(path[Math.min(t, path.length - 1)]);
      d.mesh.position.copy(world);
      d.baseY = world.y;

      d.trailPts.push(world.clone());
      if (d.trailPts.length > TRAIL_LEN) d.trailPts.shift();

      if (!skipTrail) {
        const attr = d.trail.geometry.attributes.position;
        for (let i = 0; i < d.trailPts.length; i++)
          attr.setXYZ(i, d.trailPts[i].x, d.trailPts[i].y, d.trailPts[i].z);
        attr.needsUpdate = true;
        d.trail.geometry.setDrawRange(0, d.trailPts.length);
      }
    }

    // Conflict flash — drones within 1.2 cells
    for (let i = 0; i < this.drones.length; i++)
      for (let j = i + 1; j < this.drones.length; j++)
        if (this.drones[i].mesh.position.distanceTo(this.drones[j].mesh.position) < 1.2 * CELL)
          this._flash(this.drones[i], this.drones[j]);
  }

  updateFrameLerp(paths, frame, alpha) {
    alpha = Math.max(0, Math.min(1, alpha));
    for (const d of this.drones) {
      const path = paths[String(d.id)];
      if (!path) continue;
      const wA = this._toWorld(path[Math.min(frame,     path.length - 1)]);
      const wB = this._toWorld(path[Math.min(frame + 1, path.length - 1)]);
      d.mesh.position.lerpVectors(wA, wB, alpha);
      d.baseY = d.mesh.position.y;
    }
    for (let i = 0; i < this.drones.length; i++)
      for (let j = i + 1; j < this.drones.length; j++)
        if (this.drones[i].mesh.position.distanceTo(this.drones[j].mesh.position) < 1.2 * CELL)
          this._flash(this.drones[i], this.drones[j]);
  }

  _flash(da, db) {
    [da, db].forEach(d => {
      d.mesh.material.emissiveIntensity = 3.0;
      setTimeout(() => { d.mesh.material.emissiveIntensity = 0.7; }, 100);
    });
  }

  resetForReplay(paths) {
    for (const d of this.drones) {
      const path = paths[String(d.id)];
      if (!path) continue;
      const world = this._toWorld(path[0]);
      d.mesh.position.copy(world);
      d.baseY = world.y;
      d.trailPts = [world.clone()];
      // geometry not touched: visual trail stays frozen until replay begins
    }
  }

  animateTrails() {
    const t = Date.now() * 0.002;
    this.drones.forEach((d, i) => {
      if (d.baseY !== null)
        d.mesh.position.y = d.baseY + Math.sin(t + i * 1.3) * 0.04;
      d.star.rotation.y += 0.02;
    });
  }

  dispose(scene) {
    for (const d of this.drones)
      [d.mesh, d.trail, d.ring, d.pillar, d.beacon, d.goalRing, d.star]
        .forEach(o => scene.remove(o));
    this.drones = [];
  }
}
