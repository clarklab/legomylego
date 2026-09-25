// Generic three.js viewer for brickkit exports (model.glb + model.json).
//
// GLB: one node per placed part named "p<i>" (recoloured from the colourway) and "p<i>c<code>"
// for sub-pieces with a fixed colour. Other nodes (trimesh's geometry templates) are ignored.
// Parts are drawn as one InstancedMesh per (geometry, colour), with instances sorted by the step
// in which they appear, so the build slider only changes each batch's instance count.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const NODE_RE = /^p(\d+)(?:c(\d+))?$/;
const DEG = Math.PI / 180;
const LIGHT_SCALE = 0.22;    // model.json light "power" -> three.js candela
const GLOW_SCALE = 0.55;    // glow "strength" -> emissiveIntensity
const NIGHT = { a: '#2a1c1f', b: '#07070a' };

// A soft photo-studio environment for reflections: a big bright softbox overhead, a gentler
// fill in front, a warm bounce from the floor and a darker back, all heavily blurred. Hard
// emitters (like three.js's RoomEnvironment) mirror as bright blobs on flat brick faces.
function studioEnvironment() {
  const scene = new THREE.Scene();
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(10, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {},
      vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `varying vec3 vDir;
        void main(){
          float y = vDir.y;
          vec3 top = vec3(0.92, 0.93, 0.95);
          vec3 horizon = vec3(0.62, 0.61, 0.60);
          vec3 floor = vec3(0.30, 0.27, 0.24);
          vec3 c = y > 0.0 ? mix(horizon, top, smoothstep(0.0, 0.85, y)) : mix(horizon, floor, smoothstep(0.0, 0.5, -y));
          gl_FragColor = vec4(c, 1.0);
        }`,
    }),
  );
  scene.add(dome);
  const box = (w, h, pos, look, k) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(k, k, k), side: THREE.DoubleSide }));
    m.position.set(...pos);
    m.lookAt(...look);
    scene.add(m);
  };
  box(9, 9, [0, 9, 1], [0, 0, 0], 2.4);      // overhead softbox
  box(7, 4, [-5, 3, 6], [0, 0, 0], 1.3);     // front-left fill
  box(5, 3, [6, 2, -5], [0, 0, 0], 0.8);     // rim from behind
  return scene;
}

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const lerp = (a, b, t) => a + (b - a) * t;

export function hasWebGL2() {
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch (e) {
    return false;
  }
}

// When does each node first show up in the build? Main-model parts appear at their `join` step.
// Parts of a sub-assembly appear while that sub-assembly is being built (its own steps), but only
// for the first copy that is attached after those steps; other copies appear when they join.
export function computeAppear(data) {
  const steps = data.steps || [];
  const nodes = data.nodes || [];
  const last = Math.max(0, steps.length - 1);
  const main = steps.length ? steps[last].submodel : null;
  const bySub = new Map();
  for (const s of steps) {
    if (!bySub.has(s.submodel)) bySub.set(s.submodel, []);
    bySub.get(s.submodel).push(s);
  }
  const joins = new Map();
  for (const n of nodes) {
    if (!joins.has(n.sub)) joins.set(n.sub, new Set());
    joins.get(n.sub).add(n.join ?? 0);
  }
  return nodes.map((n) => {
    const J = Math.min(Math.max(n.join ?? 0, 0), last);
    if (n.sub == null || n.sub === main) return J;
    const list = bySub.get(n.sub);
    if (!list) return J;
    let s = -1;
    for (const st of list) if (st.index <= J && st.local_step === n.local_step && st.index > s) s = st.index;
    if (s < 0) return J;
    for (const j2 of joins.get(n.sub)) if (j2 > s && j2 < J) return J;
    return s;
  });
}

function upperBound(arr, v) {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid] <= v) lo = mid + 1; else hi = mid;
  }
  return lo;
}

function cssVar(el, name, fallback) {
  const v = getComputedStyle(el).getPropertyValue(name).trim();
  return v || fallback;
}

export class ModelViewer {
  constructor(host, { onProgress, onSelect, onAutoRotate, insets, quality = 'auto', onQuality } = {}) {
    this.host = host;
    this.onProgress = onProgress || (() => {});
    this.onSelect = onSelect || (() => {});
    this.onAutoRotate = onAutoRotate || (() => {});
    this.insets = insets || (() => ({ top: 0, bottom: 0 }));
    this.tweens = new Set();
    this.visible = true;
    this.userMoved = false;
    this.variant = 0;
    this.step = Infinity;
    this.poseT = 0;
    this.lightMix = 0;
    this.selected = null;
    this.dirty = new Set();
    this.materials = new Map();
    this.batches = [];
    this.quality = quality;              // 'auto' adapts to the device; 'high' / 'low' are fixed
    this.onQuality = onQuality || (() => {});
    this.lite = false;
    this._samples = [];
    this._loop = this._loop.bind(this);
    this._raf = 0;
    this._last = 0;

    this.reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const coarse = matchMedia('(pointer: coarse)').matches;
    this.lowPower = coarse || (navigator.hardwareConcurrency || 8) <= 4;

    const renderer = (this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: false }));
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, this.lowPower ? 1.6 : 2));
    renderer.toneMapping = THREE.NeutralToneMapping;      // colour-true, made for product views
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.VSMShadowMap;
    renderer.shadowMap.autoUpdate = false;
    if (this.lowPower) renderer.transmissionResolutionScale = 0.6;
    renderer.domElement.setAttribute('aria-label', '3D model viewer. Drag to orbit, scroll or pinch to zoom.');
    renderer.domElement.setAttribute('role', 'img');
    host.prepend(renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.005, 50);

    const pmrem = new THREE.PMREMGenerator(renderer);
    this.envTex = pmrem.fromScene(studioEnvironment(), 0.06).texture;
    pmrem.dispose();
    this.scene.environment = this.envTex;

    this.bgCanvas = document.createElement('canvas');
    this.bgCanvas.width = this.bgCanvas.height = 256;
    this.bgTex = new THREE.CanvasTexture(this.bgCanvas);
    this.bgTex.colorSpace = THREE.SRGBColorSpace;
    this.scene.background = this.bgTex;
    this.refreshBackground();

    this.key = new THREE.DirectionalLight(0xffffff, 1.3);
    this.key.castShadow = true;
    this.key.shadow.mapSize.set(this.lowPower ? 1024 : 2048, this.lowPower ? 1024 : 2048);
    this.key.shadow.radius = 10;
    this.key.shadow.blurSamples = 16;
    this.key.shadow.bias = -0.0005;
    this.scene.add(this.key, this.key.target);

    // Ambient occlusion (GTAO) darkens the seams between bricks and the crevices, which is most
    // of what makes the Blender renders read as real plastic. Off on low-power devices and in
    // lite mode; the slow-frame fallback turns it off first.
    this.aoOn = this.quality === 'high' || (this.quality === 'auto' && !this.lowPower);
    if (this.aoOn) {
      this.composer = new EffectComposer(renderer);
      this.composer.addPass(new RenderPass(this.scene, this.camera));
      this.ao = new GTAOPass(this.scene, this.camera, 512, 512);
      this.ao.blendIntensity = 0.85;
      // light halos are camera-facing sprites: keep them out of the AO's depth/normal pass or
      // their quads shade the model like solid cards
      const aoRender = this.ao.render.bind(this.ao);
      this.ao.render = (...args) => {
        const halos = (this.points || []).map(({ sprite }) => sprite).filter((sp) => sp.visible);
        halos.forEach((sp) => { sp.visible = false; });
        aoRender(...args);
        halos.forEach((sp) => { sp.visible = true; });
      };
      this.composer.addPass(this.ao);
      this.composer.addPass(new OutputPass());
    }

    this.controls = new OrbitControls(this.camera, renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.rotateSpeed = 0.8;
    this.controls.zoomSpeed = 0.9;
    this.controls.screenSpacePanning = true;
    this.controls.autoRotateSpeed = 0.7;
    this.controls.addEventListener('change', () => this.requestRender());
    this.controls.addEventListener('start', () => {
      this.userMoved = true;
      this.cancelCameraTween();
      if (this.controls.autoRotate) this.setAutoRotate(false);
    });

    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.io = new IntersectionObserver((e) => {
      this.visible = e[0].isIntersecting && !document.hidden;
      if (this.visible) this.requestRender();
    });
    this.io.observe(host);
    document.addEventListener('visibilitychange', () => {
      this.visible = !document.hidden;
      if (this.visible) this.requestRender();
    });

    renderer.domElement.addEventListener('webglcontextlost', (e) => {
      e.preventDefault();
      this.host.dispatchEvent(new CustomEvent('viewer-error', { detail: 'The 3D view lost its graphics context. Reload the page to try again.' }));
    });

    this._initPicking();
    this.resize();
  }

  // ---------- loading ----------

  async load(url, data) {
    this.data = data;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Could not load the 3D model (${res.status})`);
    const total = Number(res.headers.get('content-length')) || 0;
    let buf;
    if (res.body && total) {
      const reader = res.body.getReader();
      const chunks = [];
      let got = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        got += value.length;
        this.onProgress(Math.min(1, got / total));
      }
      const all = new Uint8Array(got);
      let o = 0;
      for (const c of chunks) { all.set(c, o); o += c.length; }
      buf = all.buffer;
    } else {
      buf = await res.arrayBuffer();
    }
    this.onProgress(1);
    const gltf = await new GLTFLoader().parseAsync(buf, '');
    this._ingest(gltf.scene);
    if (this.quality === 'low') {
      this.lite = true;
      this.renderer.setPixelRatio(1);
    }
    this._setupScene();
    this._buildBatches();
    this.setStep(this.steps.length - 1);
    this.setPose(0);
    this.frame(true);
    this.introAnimation();
    this.requestRender();
  }

  _ingest(root) {
    const data = this.data;
    root.updateMatrixWorld(true);
    const nodeCount = data.nodes.length;
    this.pieces = [];
    const normalsDone = new Set();
    root.traverse((obj) => {
      if (!obj.isMesh) return;
      const m = NODE_RE.exec(obj.name) || NODE_RE.exec(obj.parent?.name || '');
      if (!m) return;
      const node = Number(m[1]);
      if (node >= nodeCount) return;
      const geom = obj.geometry;
      if (!normalsDone.has(geom)) {
        if (!geom.getAttribute('normal')) geom.computeVertexNormals();
        geom.computeBoundingBox();
        geom.computeBoundingSphere();
        normalsDone.add(geom);
      }
      this.pieces.push({ node, code: m[2] != null ? Number(m[2]) : null, geom, rest: obj.matrixWorld.clone() });
    });
    this.steps = data.steps?.length ? data.steps : [{ index: 0, submodel: null, caption: '', local_step: 0 }];
    this.appear = computeAppear(data);
    const glow = new Set(data.glow_nodes || []);
    this.nodeInfo = data.nodes.map((n, i) => ({ appear: this.appear[i] ?? 0, group: n.group || null, glow: glow.has(i), pieces: [] }));
    this.pieces.forEach((p, i) => this.nodeInfo[p.node].pieces.push(i));
    this.movingPieces = this.pieces.map((p, i) => (this.nodeInfo[p.node].group ? i : -1)).filter((i) => i >= 0);

    // bounds of the whole model at rest
    const box = new THREE.Box3();
    const b = new THREE.Box3();
    for (const p of this.pieces) box.union(b.copy(p.geom.boundingBox).applyMatrix4(p.rest));
    this.bounds = box;
    // lowest point of the model built so far, per step, so the ground can follow the build
    const lastStep = this.steps.length - 1;
    const minY = new Float64Array(lastStep + 1).fill(Infinity);
    for (const p of this.pieces) {
      const a = Math.min(lastStep, this.nodeInfo[p.node].appear);
      minY[a] = Math.min(minY[a], b.copy(p.geom.boundingBox).applyMatrix4(p.rest).min.y);
    }
    for (let i = 1; i <= lastStep; i++) minY[i] = Math.min(minY[i], minY[i - 1]);
    this.stepMinY = minY;
    this.center = box.getCenter(new THREE.Vector3());
    this.size = box.getSize(new THREE.Vector3());
    this.radius = this.size.length() / 2;

    // mechanism: decompose sampled poses so they can be interpolated (slerp) between samples
    const mech = data.mechanism;
    this.mech = null;
    if (mech && mech.samples?.length && mech.poses?.length) {
      const samples = mech.samples;
      const poses = mech.poses.map((p) => {
        const out = {};
        for (const g of mech.groups || Object.keys(p)) {
          if (!p[g]) continue;
          const M = new THREE.Matrix4().set(...p[g]);
          const pos = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
          M.decompose(pos, q, s);
          out[g] = { pos, q, s };
        }
        return out;
      });
      this.mech = { samples, poses, groups: mech.groups || [] };
      this.poseMats = Object.fromEntries(this.mech.groups.map((g) => [g, new THREE.Matrix4()]));
    }
  }

  _setupScene() {
    const { size, center, bounds } = this;
    const s = Math.max(size.x, size.y, size.z);
    this.modelSize = s;
    if (this.ao) {
      this.ao.updateGtaoMaterial({ radius: s * 0.02, distanceExponent: 1.5, thickness: s * 0.01, scale: 1.1, samples: 16 });
      this.ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    }
    this.camera.near = s / 200;
    this.camera.far = s * 40;
    this.camera.updateProjectionMatrix();
    this.controls.target.copy(center);
    this.controls.minDistance = s * 0.35;
    this.controls.maxDistance = s * 6;
    this.controls.maxPolarAngle = Math.PI * 0.58;

    const front = (this.data.front_azimuth || 0) * DEG;
    this.frontAz = front;
    // key light: high, front-left of the model's front
    const kd = new THREE.Vector3(Math.sin(front + 40 * DEG) * Math.cos(55 * DEG), Math.sin(55 * DEG), Math.cos(front + 40 * DEG) * Math.cos(55 * DEG));
    this.key.position.copy(center).addScaledVector(kd, s * 3);
    this.key.target.position.copy(center);
    const sc = this.key.shadow.camera;
    sc.left = sc.bottom = -s * 0.9;
    sc.right = sc.top = s * 0.9;
    sc.near = s * 0.5;
    sc.far = s * 6;
    sc.updateProjectionMatrix();
    this.key.shadow.normalBias = s * 0.002;

    // ground that only shows the shadow
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(s * 8, s * 8), new THREE.ShadowMaterial({ opacity: 0.2, transparent: true, depthWrite: false }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(center.x, bounds.min.y - s * 0.0005, center.z);
    ground.receiveShadow = true;
    this.ground = ground;
    this.scene.add(ground);

    // point lights (always present, intensity 0 while off, so shaders never recompile on toggle)
    this.points = [];
    const halo = this._haloTexture();
    for (const L of this.data.lights || []) {
      const pl = new THREE.PointLight(new THREE.Color(L.color || '#ffffff'), 0, 0, 2);
      pl.position.fromArray(L.pos);
      pl.userData.full = (L.power ?? 1) * LIGHT_SCALE;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: halo, color: new THREE.Color(L.color || '#ffffff'), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, depthTest: false, opacity: 0 }));
      sprite.scale.setScalar(s * 0.42);
      sprite.position.copy(pl.position);
      sprite.renderOrder = 10;
      this.scene.add(pl, sprite);
      this.points.push({ light: pl, sprite });
    }
    const strengths = (this.data.glow || []).map((g) => g.strength).filter((x) => x > 0);
    this.glowStrength = (strengths.length ? Math.max(...strengths) : 3) * GLOW_SCALE;
  }

  _haloTexture() {
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d');
    const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    grd.addColorStop(0, 'rgba(255,255,255,0.9)');
    grd.addColorStop(0.18, 'rgba(255,255,255,0.45)');
    grd.addColorStop(0.5, 'rgba(255,255,255,0.1)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, 128, 128);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }

  // ---------- materials ----------

  _material(code, glow) {
    const key = `${code}${glow ? 'g' : ''}`;
    let m = this.materials.get(key);
    if (m) return m;
    const c = this.data.colors?.[code] || this.data.colors?.[String(code)] || { hex: '#9ba19d', alpha: 255, material: '' };
    const color = new THREE.Color(c.hex || '#9ba19d');
    const trans = (c.alpha ?? 255) < 255;
    const kind = String(c.material || '').toLowerCase();
    const white = new THREE.Color(1, 1, 1);
    // ABS: satin, not glossy. A broad soft sheen from the studio, no clear coat.
    const p = {
      color,
      roughness: 0.34,
      metalness: 0,
      specularIntensity: 0.65,
      envMapIntensity: 0.9,
    };
    let glowBase = 0;
    if (trans && glow) {
      // Light-emitting translucent pieces (LED lenses, glowing cores) are drawn as luminous, non-
      // transmissive plastic: three.js transmission only shows opaque objects behind a surface,
      // so this keeps them visible through other translucent parts.
      Object.assign(p, { roughness: 0.2, specularIntensity: 0.8 });
      glowBase = 0.35;
    } else if (trans) {
      Object.assign(p, {
        color: color.clone().lerp(white, 0.45),
        roughness: 0.08,
        transmission: 1,
        thickness: this.modelSize * 0.01,
        ior: 1.58,
        attenuationColor: color.clone().lerp(white, 0.15),
        attenuationDistance: this.modelSize * 0.09,
        specularIntensity: 0.7,
        side: THREE.DoubleSide,
      });
      if (kind.includes('glitter') || kind.includes('speckle')) p.roughness = 0.2;
    } else if (kind === 'chrome') {
      Object.assign(p, { metalness: 1, roughness: 0.12 });
    } else if (kind === 'metal' || kind === 'metallic') {
      Object.assign(p, { metalness: 0.9, roughness: 0.35 });
    } else if (kind === 'pearlescent' || kind === 'pearl') {
      Object.assign(p, { metalness: 0.45, roughness: 0.32 });
    } else if (kind === 'rubber') {
      Object.assign(p, { roughness: 0.82, specularIntensity: 0.3 });
    } else if (kind === 'glitter' || kind === 'speckle') {
      Object.assign(p, { roughness: 0.35, metalness: 0.15 });
    } else if (kind === 'milky' || kind === 'glow') {
      Object.assign(p, { roughness: 0.35, transmission: 0.35, thickness: this.modelSize * 0.01, ior: 1.5 });
    }
    if (glow) {
      p.emissive = color.clone();
      p.emissiveIntensity = glowBase;
    }
    m = new THREE.MeshPhysicalMaterial(p);
    m.userData.trans = trans && !glow;
    m.userData.full = { transmission: m.transmission, side: m.side };
    if (m.userData.trans && this.lite) this._liteMaterial(m, true);
    m.userData.glow = glow;
    m.userData.glowBase = glowBase;
    this.materials.set(key, m);
    return m;
  }

  // Lite mode: translucent parts use plain alpha blending instead of the (costly) transmission pass.
  _liteMaterial(m, on) {
    if (on) {
      Object.assign(m, { transmission: 0, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.FrontSide });
    } else {
      Object.assign(m, { transmission: m.userData.full.transmission, transparent: false, opacity: 1, depthWrite: true, side: m.userData.full.side });
    }
    m.needsUpdate = true;
  }

  setLite(on) {
    this.lite = !!on;
    if (this.lite) this.aoOn = false;
    for (const m of this.materials.values()) if (m.userData.trans) this._liteMaterial(m, this.lite);
    this.onQuality(this.lite ? 'lite' : 'full');
    this.requestRender();
  }

  // Called with the frame time of each continuous animation frame; degrades once per slow streak.
  _perfSample(dt) {
    if (this.quality !== 'auto') return;
    this._samples.push(dt);
    if (this._samples.length < 20) return;
    const sorted = this._samples.sort((a, b) => a - b);
    const median = sorted[10];
    this._samples = [];
    if (median < 0.045) return;
    const pr = this.renderer.getPixelRatio();
    if (this.aoOn) {
      this.aoOn = false;                         // the cheapest big saving goes first
      this.requestRender();
    } else if (pr > 1.01) {
      this.renderer.setPixelRatio(Math.max(1, pr * 0.7));
      this.resize();
    } else if (!this.lite) {
      this.setLite(true);
    }
  }

  // ---------- batches ----------

  _buildBatches() {
    for (const b of this.batches) {
      this.scene.remove(b.mesh);
      b.mesh.dispose();
    }
    const colors = this.data.variants?.[this.variant]?.colors || this.data.variants?.[0]?.colors || [];
    const groups = new Map();
    this.pieces.forEach((p, i) => {
      const info = this.nodeInfo[p.node];
      const code = p.code != null ? p.code : (colors[p.node] ?? 16);
      const glow = info.glow;
      const key = `${p.geom.uuid}|${code}|${glow ? 1 : 0}`;
      let g = groups.get(key);
      if (!g) groups.set(key, (g = { geom: p.geom, code, glow, pieces: [] }));
      g.pieces.push(i);
    });
    this.batches = [];
    this.pieceSlot = new Array(this.pieces.length);
    for (const g of groups.values()) {
      g.pieces.sort((a, b) => this.nodeInfo[this.pieces[a].node].appear - this.nodeInfo[this.pieces[b].node].appear || a - b);
      const mat = this._material(g.code, g.glow);
      const mesh = new THREE.InstancedMesh(g.geom, mat, g.pieces.length);
      mesh.frustumCulled = false;
      mesh.castShadow = !mat.userData.trans;
      mesh.receiveShadow = false;
      const batch = { mesh, pieces: g.pieces, appears: Int32Array.from(g.pieces, (pi) => this.nodeInfo[this.pieces[pi].node].appear), code: g.code };
      mesh.userData.batch = batch;
      g.pieces.forEach((pi, idx) => {
        this.pieceSlot[pi] = { batch, index: idx };
        mesh.setMatrixAt(idx, this.pieces[pi].rest);
      });
      if (g.pieces.some((pi) => this.nodeInfo[this.pieces[pi].node].group)) mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      this.batches.push(batch);
      this.scene.add(mesh);
    }
    this.batchMeshes = this.batches.map((b) => b.mesh);
    this.drops = new Map();
    this._applyCounts();
    if (this.mech) this.setPose(this.poseT);
    this._applyGlow();
    this._refreshSelection();
    this.renderer.shadowMap.needsUpdate = true;
  }

  _writePiece(pi, M = new THREE.Matrix4()) {
    const slot = this.pieceSlot[pi];
    if (!slot) return;
    const p = this.pieces[pi];
    M.copy(p.rest);
    const g = this.nodeInfo[p.node].group;
    if (g && this.poseMats?.[g]) M.premultiply(this.poseMats[g]);
    const dy = this.drops.get(pi);
    if (dy) M.elements[13] += dy;
    slot.batch.mesh.setMatrixAt(slot.index, M);
    this.dirty.add(slot.batch);
  }

  _flush() {
    if (!this.dirty.size) return;
    for (const b of this.dirty) b.mesh.instanceMatrix.needsUpdate = true;
    this.dirty.clear();
    this.renderer.shadowMap.needsUpdate = true;
    if (this.selected != null) this._refreshSelection();
  }

  _applyCounts() {
    for (const b of this.batches) b.mesh.count = upperBound(b.appears, this.step);
    this.renderer.shadowMap.needsUpdate = true;
  }

  // ---------- public controls ----------

  setVariant(k) {
    if (!this.pieces || k === this.variant) return;
    this.variant = k;
    this._buildBatches();
    this.requestRender();
  }

  /** Show every node whose appear step <= step. With animate, newly added parts drop into place. */
  setStep(step, { animate = false } = {}) {
    if (!this.pieces) return;
    const last = this.steps.length - 1;
    step = Math.max(0, Math.min(last, Math.round(step)));
    const prev = this.step;
    this.step = step;
    // finish any running drops
    if (this.drops.size) {
      const done = [...this.drops.keys()];
      this.drops.clear();
      for (const pi of done) this._writePiece(pi);
    }
    this._applyCounts();
    this._moveGround(animate);
    if (animate && step > prev && Number.isFinite(prev)) {
      const fresh = [];
      this.pieces.forEach((p, i) => {
        const a = this.nodeInfo[p.node].appear;
        if (a > prev && a <= step) fresh.push(i);
      });
      if (fresh.length && fresh.length < 600 && !this.reducedMotion) this._dropIn(fresh);
    }
    this.requestRender();
  }

  _moveGround(animate) {
    if (!this.ground) return;
    const y = this.stepMinY?.[this.step];
    const to = (Number.isFinite(y) ? y : this.bounds.min.y) - this.modelSize * 0.0005;
    const from = this.ground.position.y;
    if (Math.abs(to - from) < 1e-6) return;
    if (this._groundTween) this.tweens.delete(this._groundTween);
    if (!animate) {
      this.ground.position.y = to;
      this.renderer.shadowMap.needsUpdate = true;
      return;
    }
    const start = performance.now();
    this._groundTween = {
      update: (now) => {
        const t = Math.min(1, (now - start) / 380);
        this.ground.position.y = lerp(from, to, easeInOut(t));
        this.renderer.shadowMap.needsUpdate = true;
        return t < 1;
      },
    };
    this.tweens.add(this._groundTween);
  }

  _dropIn(list) {
    const h = this.modelSize * 0.09;
    const dur = 460;
    const start = performance.now();
    const delays = new Map();
    // stagger by node so a part and its sub-pieces move together
    const nodeDelay = new Map();
    for (const pi of list) {
      const n = this.pieces[pi].node;
      if (!nodeDelay.has(n)) nodeDelay.set(n, Math.random() * Math.min(220, 30 * nodeDelay.size));
      delays.set(pi, nodeDelay.get(n));
      this.drops.set(pi, h);
      this._writePiece(pi);
    }
    const tw = {
      update: (now) => {
        let alive = false;
        for (const pi of list) {
          if (!this.drops.has(pi)) continue;
          const t = Math.min(1, Math.max(0, (now - start - delays.get(pi)) / dur));
          if (t >= 1) this.drops.delete(pi); else { this.drops.set(pi, h * (1 - easeOut(t))); alive = true; }
          this._writePiece(pi);
        }
        return alive;
      },
    };
    this.tweens.add(tw);
  }

  /** Mechanism pose, t in [0, 1]. */
  setPose(t) {
    if (!this.mech) return;
    this.poseT = t = Math.max(0, Math.min(1, t));
    const { samples, poses, groups } = this.mech;
    let i = upperBound(samples, t) - 1;
    i = Math.max(0, Math.min(samples.length - 2, i));
    const span = samples[i + 1] - samples[i];
    const f = samples.length > 1 && span > 0 ? Math.min(1, Math.max(0, (t - samples[i]) / span)) : 0;
    const A = poses[i], B = poses[Math.min(i + 1, poses.length - 1)];
    const pos = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
    const I = { pos: new THREE.Vector3(), q: new THREE.Quaternion(), s: new THREE.Vector3(1, 1, 1) };
    for (const g of groups) {
      const a = A?.[g] || I, b = B?.[g] || I;
      pos.lerpVectors(a.pos, b.pos, f);
      q.slerpQuaternions(a.q, b.q, f);
      s.lerpVectors(a.s, b.s, f);
      this.poseMats[g].compose(pos, q, s);
    }
    const M = new THREE.Matrix4();
    for (const pi of this.movingPieces) this._writePiece(pi, M);
    this.requestRender();
  }

  setLights(on) {
    if (!this.pieces) return;
    const from = this.lightMix, to = on ? 1 : 0;
    const start = performance.now(), dur = 650;
    if (this._lightTween) this.tweens.delete(this._lightTween);
    this._lightTween = {
      update: (now) => {
        const t = Math.min(1, (now - start) / dur);
        this.lightMix = lerp(from, to, easeInOut(t));
        this._applyGlow();
        return t < 1;
      },
    };
    this.tweens.add(this._lightTween);
    this.requestRender();
  }

  _applyGlow() {
    const k = this.lightMix || 0;
    this.scene.environmentIntensity = lerp(1, 0.16, k);
    this.key.intensity = lerp(1.3, 0.12, k);
    if (this.ground) this.ground.material.opacity = lerp(0.2, 0.08, k);
    for (const { light, sprite } of this.points || []) {
      light.intensity = light.userData.full * k;
      sprite.material.opacity = 0.9 * k;
    }
    for (const m of this.materials.values()) if (m.userData.glow) m.emissiveIntensity = m.userData.glowBase + this.glowStrength * k;
    this._paintBackground(k);
  }

  refreshBackground() {
    this.dayBg = { a: cssVar(this.host, '--stage-a', '#f8f5ee'), b: cssVar(this.host, '--stage-b', '#e7e2d6') };
    this._paintBackground(this.lightMix || 0);
    this.requestRender();
  }

  _paintBackground(k) {
    const g = this.bgCanvas.getContext('2d');
    const w = this.bgCanvas.width;
    const ca = new THREE.Color(this.dayBg.a).lerp(new THREE.Color(NIGHT.a), k);
    const cb = new THREE.Color(this.dayBg.b).lerp(new THREE.Color(NIGHT.b), k);
    const grd = g.createRadialGradient(w / 2, w * 0.38, 0, w / 2, w * 0.38, w * 0.78);
    grd.addColorStop(0, `#${ca.getHexString()}`);
    grd.addColorStop(1, `#${cb.getHexString()}`);
    g.fillStyle = grd;
    g.fillRect(0, 0, w, w);
    this.bgTex.needsUpdate = true;
  }

  setAutoRotate(on) {
    this.controls.autoRotate = !!on;
    this.onAutoRotate(!!on);
    this.requestRender();
  }

  // ---------- camera ----------

  _viewOffset() {
    const w = this.host.clientWidth || 1, h = this.host.clientHeight || 1;
    const { top = 0, bottom = 0 } = this.insets() || {};
    const usable = Math.max(0.35, (h - top - bottom) / h);
    const off = (bottom - top) / 2;
    return { w, h, usable, off };
  }

  _fitDistance(az, el) {
    const { w, h, usable } = this._viewOffset();
    const aspect = w / h;
    const tanV = Math.tan((this.camera.fov * DEG) / 2) * usable * 0.97;
    const tanH = Math.tan((this.camera.fov * DEG) / 2) * aspect * 0.9;
    const d = new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
    const right = new THREE.Vector3(0, 1, 0).cross(d).normalize();
    const up = d.clone().cross(right).normalize();
    const b = this.bounds;
    let D = 0;
    const p = new THREE.Vector3();
    for (const x of [b.min.x, b.max.x]) for (const y of [b.min.y, b.max.y]) for (const z of [b.min.z, b.max.z]) {
      p.set(x, y, z).sub(this.center);
      const px = p.dot(right), py = p.dot(up), pz = p.dot(d);
      D = Math.max(D, pz + Math.abs(px) / tanH, pz + Math.abs(py) / tanV);
    }
    return { D, dir: d };
  }

  homeView() {
    const az = this.frontAz + 32 * DEG;
    const el = 16 * DEG;
    const { D, dir } = this._fitDistance(az, el);
    return { position: this.center.clone().addScaledVector(dir, D), target: this.center.clone() };
  }

  frame(immediate = false) {
    const v = this.homeView();
    if (immediate) {
      this.camera.position.copy(v.position);
      this.controls.target.copy(v.target);
      this.controls.update();
    } else {
      this.tweenCamera(v.position, v.target, 900);
    }
    this.requestRender();
  }

  resetView() {
    this.userMoved = false;
    this.frame(false);
  }

  introAnimation() {
    if (this.reducedMotion) return this.frame(true);
    const end = this.homeView();
    const off = end.position.clone().sub(end.target);
    const start = off.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -38 * DEG).multiplyScalar(1.45).add(end.target);
    start.y += this.modelSize * 0.25;
    this.camera.position.copy(start);
    this.controls.target.copy(end.target);
    this.tweenCamera(end.position, end.target, 1500);
  }

  tweenCamera(toPos, toTarget, dur = 900) {
    this.cancelCameraTween();
    const fromPos = this.camera.position.clone(), fromTarget = this.controls.target.clone();
    // interpolate in spherical coordinates around the target so the camera arcs instead of cutting through
    const s0 = new THREE.Spherical().setFromVector3(fromPos.clone().sub(fromTarget));
    const s1 = new THREE.Spherical().setFromVector3(toPos.clone().sub(toTarget));
    let dTheta = s1.theta - s0.theta;
    while (dTheta > Math.PI) dTheta -= 2 * Math.PI;
    while (dTheta < -Math.PI) dTheta += 2 * Math.PI;
    const start = performance.now();
    const sp = new THREE.Spherical();
    const tw = {
      update: (now) => {
        const t = Math.min(1, (now - start) / dur), e = easeInOut(t);
        sp.set(lerp(s0.radius, s1.radius, e), lerp(s0.phi, s1.phi, e), s0.theta + dTheta * e);
        this.controls.target.lerpVectors(fromTarget, toTarget, e);
        this.camera.position.setFromSpherical(sp).add(this.controls.target);
        this.camera.lookAt(this.controls.target);
        return t < 1;
      },
    };
    this._camTween = tw;
    this.tweens.add(tw);
    this.requestRender();
  }

  cancelCameraTween() {
    if (this._camTween) this.tweens.delete(this._camTween);
    this._camTween = null;
  }

  resize() {
    const { w, h, off } = this._viewOffset();
    this.renderer.setSize(w, h, false);
    if (this.composer) {
      this.composer.setPixelRatio(this.renderer.getPixelRatio());
      this.composer.setSize(w, h);
    }
    this.camera.aspect = w / h;
    this.camera.setViewOffset(w, h, 0, off, w, h);
    this.camera.updateProjectionMatrix();
    if (this.bounds && !this.userMoved && !this._camTween) this.frame(true);
    this.requestRender();
  }

  // ---------- picking ----------

  _initPicking() {
    const el = this.renderer.domElement;
    this.raycaster = new THREE.Raycaster();
    let down = null;
    el.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
    el.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      const quick = performance.now() - down.t < 450;
      down = null;
      if (moved < 6 && quick) this._pick(e);
    });
    this.hlMat = new THREE.MeshBasicMaterial({ color: 0xffd60a, transparent: true, opacity: 0.6, depthTest: false, depthWrite: false });
    this.hlGroup = new THREE.Group();
    this.hlGroup.renderOrder = 20;
    this.scene.add(this.hlGroup);
  }

  _pick(e) {
    if (!this.batchMeshes) return;
    const r = this.renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.camera.updateMatrixWorld();
    this.raycaster.setFromCamera(ndc, this.camera);
    for (const m of this.batchMeshes) m.boundingSphere = null;
    const hits = this.raycaster.intersectObjects(this.batchMeshes.filter((m) => m.count > 0), false);
    const hit = hits.find((h) => h.instanceId != null);
    if (!hit) return this.select(null);
    const pi = hit.object.userData.batch.pieces[hit.instanceId];
    const node = this.pieces[pi].node;
    this.select(this.selected === node ? null : node);
  }

  select(node) {
    this.selected = node;
    this._refreshSelection();
    this.onSelect(node);
    this.requestRender();
  }

  _refreshSelection() {
    const g = this.hlGroup;
    if (!g) return;
    while (g.children.length) g.remove(g.children[0]);
    if (this.selected == null || !this.nodeInfo?.[this.selected]) return;
    const M = new THREE.Matrix4();
    for (const pi of this.nodeInfo[this.selected].pieces) {
      const slot = this.pieceSlot[pi];
      if (!slot || slot.index >= slot.batch.mesh.count) continue;
      slot.batch.mesh.getMatrixAt(slot.index, M);
      const m = new THREE.Mesh(this.pieces[pi].geom, this.hlMat);
      m.matrixAutoUpdate = false;
      m.matrix.copy(M);
      m.renderOrder = 20;
      g.add(m);
    }
  }

  // ---------- loop ----------

  requestRender() {
    if (!this._raf) this._raf = requestAnimationFrame(this._loop);
  }

  _loop(now) {
    this._raf = 0;
    const raw = this._last ? (now - this._last) / 1000 : 0;
    const dt = raw ? Math.min(0.1, raw) : 1 / 60;
    if (raw) this._perfSample(raw);
    this._last = now;
    let active = false;
    for (const tw of [...this.tweens]) {
      if (tw.update(now)) active = true; else this.tweens.delete(tw);
    }
    if (this.controls.update(dt)) active = true;
    if (this.controls.autoRotate) active = true;
    this._flush();
    if (this.aoOn && this.composer) this.composer.render(dt);
    else this.renderer.render(this.scene, this.camera);
    if (active && this.visible) this.requestRender();
    else if (!this._raf) this._last = 0;
  }
}
