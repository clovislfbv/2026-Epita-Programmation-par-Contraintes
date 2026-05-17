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

  update()  { this.controls.update(); }
  render()  { this.renderer.render(this.scene, this.camera); }

  onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }
}
