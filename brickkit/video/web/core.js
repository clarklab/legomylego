/* brickkit showreel compositor: core.
 *
 * Deterministic: renderFrame(f) draws video frame f from the reel plan (reel.json, see
 * brickkit/video/reel.py) and the Blender plates, and nothing else - no clocks, no Math.random.
 * Everything is drawn in a 1080 x 1080 logical space and scaled to the canvas.
 *
 * Files: core.js (maths, assets, drawing primitives, 3D projection, frame loop),
 * segments.js (one drawer per segment), fx.js (transitions, grading, post effects).
 */
'use strict';

const L = 1080;                 // logical frame size
const M = 64;                   // safe margin
let D = null;                   // the reel plan
let TH = null;                  // theme tokens
let S = 1;                      // canvas px per logical px
let CV = null, CX = null;       // main canvas + context
const IMG = new Map();          // url -> ImageBitmap | null
let WIRE = null;                // {xyz: Float32Array, part: Uint16Array, count}
const OFF = {};                 // offscreen canvases by name
let F = 0;                      // frame being drawn

// ------------------------------------------------------------------------------ maths
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ramp = (f, a, b) => clamp((f - a) / Math.max(1e-6, b - a));
const E = {
  lin: t => t,
  inQuad: t => t * t,
  outQuad: t => 1 - (1 - t) * (1 - t),
  inCubic: t => t * t * t,
  outCubic: t => 1 - Math.pow(1 - t, 3),
  inOutCubic: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outQuint: t => 1 - Math.pow(1 - t, 5),
  inOutQuint: t => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2),
  outExpo: t => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  inExpo: t => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10)),
  inOutExpo: t => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2
    : (2 - Math.pow(2, -20 * t + 10)) / 2),
  outBack: (t, s = 1.70158) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2),
  inBack: (t, s = 1.70158) => (s + 1) * t * t * t - s * t * t,
  // damped spring from 0 to 1: overshoots and settles (f wobbles, d damping)
  spring: (t, f = 2.2, d = 6.5) => (t <= 0 ? 0 : 1 - Math.exp(-d * t) * Math.cos(f * 2 * Math.PI * t)),
  smooth: t => t * t * t * (t * (6 * t - 15) + 10),
};
// animate: eased 0..1 between frames a and b
const tw = (f, a, b, ease = E.outCubic) => ease(ramp(f, a, b));

function rng(seed) {                      // mulberry32
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const hash = (a, b = 0) => rng((a * 73856093) ^ (b * 19349663))();

// ------------------------------------------------------------------------------ colour
function rgb(hex) {
  const h = String(hex).replace('#', '');
  const v = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
  return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)];
}
function rgba(hex, a = 1) {
  if (String(hex).startsWith('rgba')) return hex;
  const [r, g, b] = rgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}
function mix(a, b, t) {
  const A = rgb(a), B = rgb(b);
  const c = A.map((v, i) => Math.round(lerp(v, B[i], t)));
  return '#' + c.map(v => v.toString(16).padStart(2, '0')).join('');
}
function luma(hex) {
  const [r, g, b] = rgb(hex).map(v => v / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const onColour = hex => (luma(hex) > 0.55 ? '#111010' : '#FFFCF3');

// ------------------------------------------------------------------------------ assets
async function img(url) {
  if (!url) return null;
  if (IMG.has(url)) return IMG.get(url);
  let bm = null;
  try {
    const r = await fetch(url);
    if (r.ok) bm = await createImageBitmap(await r.blob());
  } catch (e) { bm = null; }
  IMG.set(url, bm);
  return bm;
}
function forget(prefix) {                 // drop cached plates we've moved past
  for (const [k, v] of IMG) {
    if (k.startsWith(prefix)) { if (v && v.close) v.close(); IMG.delete(k); }
  }
}

async function loadFonts() {
  const faces = [
    ['Fredoka', 'fonts/Fredoka.ttf', { weight: '300 700', stretch: '75% 125%' }],
    ['Space Mono', 'fonts/SpaceMono-Regular.ttf', { weight: '400' }],
    ['Space Mono', 'fonts/SpaceMono-Bold.ttf', { weight: '700' }],
    ['Share Tech Mono', 'fonts/ShareTechMono-Regular.ttf', { weight: '400' }],
    ['VT323', 'fonts/VT323-Regular.ttf', { weight: '400' }],
  ];
  for (const [fam, url, desc] of faces) {
    const ff = new FontFace(fam, `url(${url})`, desc);
    await ff.load();
    document.fonts.add(ff);
  }
}

function off(name, w = L, h = L) {        // an offscreen canvas at device resolution
  let c = OFF[name];
  const W = Math.round(w * S), H = Math.round(h * S);
  if (!c || c.width !== W || c.height !== H) {
    c = OFF[name] = document.createElement('canvas');
    c.width = W; c.height = H;
  }
  const x = c.getContext('2d');
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.clearRect(0, 0, W, H);
  x.setTransform(S, 0, 0, S, 0, 0);
  return [c, x];
}

// the logo file sits on a flat yellow card: key that yellow out (sampled from its corner) so
// the logo lands on whatever is behind it
function keyLogo() {
  const bm = IMG.get(D.logo);
  if (!bm) return;
  const c = document.createElement('canvas');
  c.width = bm.width; c.height = bm.height;
  const x = c.getContext('2d', { willReadFrequently: true });
  x.drawImage(bm, 0, 0);
  const im = x.getImageData(0, 0, c.width, c.height);
  const d = im.data;
  const [r0, g0, b0] = [d[0], d[1], d[2]];
  for (let i = 0; i < d.length; i += 4) {
    const dist = Math.hypot(d[i] - r0, d[i + 1] - g0, d[i + 2] - b0);
    d[i + 3] = Math.round(d[i + 3] * clamp((dist - 22) / 40));
  }
  x.putImageData(im, 0, 0);
  IMG.set(D.logo, c);
}

// ------------------------------------------------------------------------------ text
const MONO_UPPER = () => TH.mono !== 'Fredoka';
function font(size, weight = 700, fam = null, stretch = null) {
  const f = fam || TH.display;
  return `${stretch ? stretch + ' ' : ''}${weight} ${size}px "${f}"`;
}
function monoFont(size) { return font(size, TH.mono === 'Fredoka' ? 600 : 400, TH.mono); }

function measure(str, fnt, spacing = 0, c = CX) {
  c.save(); c.font = fnt; c.letterSpacing = `${spacing}px`;
  const w = c.measureText(str).width;
  c.restore();
  return w;
}
// size that fits `str` in `maxW` (never above `size`)
function fitSize(str, size, maxW, weight = 700, fam = null, spacing = 0) {
  const w = measure(str, font(size, weight, fam), spacing * size);
  return w <= maxW ? size : Math.floor(size * maxW / w);
}
function text(str, x, y, o = {}) {
  const c = o.ctx || CX;
  c.save();
  c.font = o.font || font(o.size || 40, o.weight || 700, o.fam);
  c.letterSpacing = `${o.spacing || 0}px`;
  c.textAlign = o.align || 'left';
  c.textBaseline = o.base || 'alphabetic';
  c.globalAlpha *= o.alpha === undefined ? 1 : o.alpha;     // fades set on the context carry
  if (o.shadow) { c.shadowColor = o.shadow; c.shadowBlur = o.blur || 0; c.shadowOffsetX = o.sx || 0; c.shadowOffsetY = o.sy || 0; }
  if (o.stroke) { c.lineWidth = o.lw || 4; c.strokeStyle = o.stroke; c.lineJoin = 'round'; c.strokeText(str, x, y); }
  c.fillStyle = o.color || TH.ink;
  c.fillText(str, x, y);
  c.restore();
}
// glyph advances (prefix widths, so kerning and spacing are kept)
function glyphs(str, fnt, spacing = 0) {
  const out = [];
  CX.save(); CX.font = fnt; CX.letterSpacing = `${spacing}px`;
  let prev = 0;
  const chars = Array.from(str);
  for (let i = 0; i < chars.length; i++) {
    const w = CX.measureText(chars.slice(0, i + 1).join('')).width;
    out.push({ ch: chars[i], x: prev, w: w - prev });
    prev = w;
  }
  CX.restore();
  return { list: out, width: prev };
}
// draw text glyph by glyph; fn(i, n) -> {dx, dy, sx, sy, rot, alpha, color, ch}
function kinetic(str, x, y, fnt, fn, o = {}) {
  const g = glyphs(str, fnt, o.spacing || 0);
  const x0 = o.align === 'center' ? x - g.width / 2 : o.align === 'right' ? x - g.width : x;
  const n = g.list.length;
  CX.save(); CX.font = fnt; CX.textBaseline = o.base || 'alphabetic';
  g.list.forEach((gl, i) => {
    if (gl.ch === ' ') return;
    const t = fn(i, n, gl) || {};
    const a = t.alpha === undefined ? 1 : t.alpha;
    if (a <= 0.001) return;
    CX.save();
    const cxp = x0 + gl.x + gl.w / 2 + (t.dx || 0), cyp = y + (t.dy || 0);
    CX.translate(cxp, cyp);
    if (t.rot) CX.rotate(t.rot);
    CX.scale(t.sx === undefined ? 1 : t.sx, t.sy === undefined ? (t.sx === undefined ? 1 : t.sx) : t.sy);
    CX.globalAlpha *= a;
    CX.textAlign = 'center';
    if (o.stroke) { CX.lineWidth = o.lw || 6; CX.strokeStyle = o.stroke; CX.lineJoin = 'round'; CX.strokeText(t.ch || gl.ch, 0, 0); }
    CX.fillStyle = t.color || o.color || TH.ink;
    CX.fillText(t.ch || gl.ch, 0, 0);
    CX.restore();
  });
  CX.restore();
  return g.width;
}

// ------------------------------------------------------------------------------ shapes
function rrect(x, y, w, h, r, c = CX) {
  c.beginPath();
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  c.roundRect(x, y, w, h, r);
}
function circle(x, y, r, c = CX) { c.beginPath(); c.arc(x, y, Math.max(0, r), 0, Math.PI * 2); }

// a stud seen from above: side ring plus a lighter top face nudged up
function stud(x, y, r, col, c = CX, a = 1) {
  if (r <= 0.2) return;
  c.save(); c.globalAlpha *= a;
  c.fillStyle = mix(col, '#000000', 0.18); circle(x, y + r * 0.1, r, c); c.fill();
  c.fillStyle = col; circle(x, y - r * 0.04, r * 0.9, c); c.fill();
  c.fillStyle = rgba('#ffffff', 0.18); circle(x - r * 0.18, y - r * 0.24, r * 0.46, c); c.fill();
  c.restore();
}
// a brick from above (cols x rows studs), centred; unit = one stud pitch
function brickTop(x, y, cols, rows, unit, col, c = CX) {
  const w = cols * unit, h = rows * unit;
  c.save();
  c.fillStyle = mix(col, '#000000', 0.22);
  rrect(x - w / 2, y - h / 2 + unit * 0.08, w, h, unit * 0.12, c); c.fill();
  c.fillStyle = col;
  rrect(x - w / 2, y - h / 2, w, h, unit * 0.12, c); c.fill();
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
    stud(x - w / 2 + unit * (i + 0.5), y - h / 2 + unit * (j + 0.5), unit * 0.3, col, c);
  }
  c.restore();
}
// a brick seen from the front: body plus studs along the top
function brickFront(x, y, w, h, col, studs, c = CX) {
  c.save();
  const sw = h * 0.42, sh = h * 0.2;
  c.fillStyle = col;
  for (let i = 0; i < studs; i++) {
    const sx = x + w * (i + 0.5) / studs - sw / 2;
    rrect(sx, y - sh, sw, sh + 2, 3, c); c.fill();
  }
  rrect(x, y, w, h, 4, c); c.fill();
  c.fillStyle = rgba('#ffffff', 0.16); c.fillRect(x + 4, y + 3, w - 8, h * 0.18);
  c.fillStyle = rgba('#000000', 0.18); c.fillRect(x + 4, y + h * 0.8, w - 8, h * 0.2 - 3);
  c.restore();
}
function checkMark(x, y, s, col, p = 1, lw = null, c = CX) {
  const pts = [[-0.42, 0.02], [-0.12, 0.32], [0.46, -0.3]];
  c.save(); c.strokeStyle = col; c.lineWidth = lw || s * 0.16; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath();
  const L1 = Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]);
  const L2 = Math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]);
  const d = p * (L1 + L2);
  c.moveTo(x + pts[0][0] * s, y + pts[0][1] * s);
  if (d <= L1) {
    const t = d / L1;
    c.lineTo(x + lerp(pts[0][0], pts[1][0], t) * s, y + lerp(pts[0][1], pts[1][1], t) * s);
  } else {
    const t = (d - L1) / L2;
    c.lineTo(x + pts[1][0] * s, y + pts[1][1] * s);
    c.lineTo(x + lerp(pts[1][0], pts[2][0], t) * s, y + lerp(pts[1][1], pts[2][1], t) * s);
  }
  c.stroke(); c.restore();
}
// corner brackets round a box (HUD reticle)
function brackets(x0, y0, x1, y1, len, col, lw = 3, c = CX, a = 1) {
  c.save(); c.globalAlpha *= a; c.strokeStyle = col; c.lineWidth = lw; c.lineCap = 'square';
  c.beginPath();
  for (const [x, y, sx, sy] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]]) {
    c.moveTo(x, y + sy * len); c.lineTo(x, y); c.lineTo(x + sx * len, y);
  }
  c.stroke(); c.restore();
}
function pawPrint(x, y, s, col, rot = 0, c = CX, a = 1) {
  c.save(); c.globalAlpha *= a; c.translate(x, y); c.rotate(rot); c.fillStyle = col;
  c.beginPath(); c.ellipse(0, s * 0.18, s * 0.34, s * 0.28, 0, 0, Math.PI * 2); c.fill();
  for (const [tx, ty] of [[-0.36, -0.2], [-0.13, -0.42], [0.13, -0.42], [0.36, -0.2]]) {
    c.beginPath(); c.ellipse(tx * s, ty * s, s * 0.12, s * 0.15, 0, 0, Math.PI * 2); c.fill();
  }
  c.restore();
}

// ------------------------------------------------------------------------------ 3D
// the video camera at frame f: Blender track-to (-Z at the target, Y up), 36 mm across
function camAt(f) {
  const C = D.camera;
  const k = Math.max(0, Math.min(C.pos.length - 1, f - C.start));
  const p = C.pos[k], t = C.target[k];
  let fx = t[0] - p[0], fy = t[1] - p[1], fz = t[2] - p[2];
  const fn = Math.hypot(fx, fy, fz); fx /= fn; fy /= fn; fz /= fn;
  // up = (0,-1,0) minus its component along f
  let ux = -fx * (-fy), uy = -1 - fy * (-fy), uz = -fz * (-fy);
  const un = Math.hypot(ux, uy, uz); ux /= un; uy /= un; uz /= un;
  const rx = fy * uz - fz * uy, ry = fz * ux - fx * uz, rz = fx * uy - fy * ux;   // r = f x u
  return { p, f: [fx, fy, fz], u: [ux, uy, uz], r: [rx, ry, rz], k: C.lens[k] / 36 * L, dist: fn };
}
function proj(cam, x, y, z) {
  const dx = x - cam.p[0], dy = y - cam.p[1], dz = z - cam.p[2];
  const zc = dx * cam.f[0] + dy * cam.f[1] + dz * cam.f[2];
  const s = cam.k / Math.max(zc, 1e-6);
  return [L / 2 + (dx * cam.r[0] + dy * cam.r[1] + dz * cam.r[2]) * s,
    L / 2 - (dx * cam.u[0] + dy * cam.u[1] + dz * cam.u[2]) * s, zc];
}

async function loadWire() {
  if (!D.wire || !D.wire.count) return;
  const r = await fetch(D.wire.url);
  if (!r.ok) return;
  const buf = await r.arrayBuffer();
  const n = D.wire.count;
  WIRE = { xyz: new Float32Array(buf, 0, n * 6), part: new Uint16Array(buf, n * 24, n), count: n };
}

// the parts' LDraw edges projected through the camera, stroked additively in depth buckets.
// o: {parts: Set|null, groups: [[16]]|null (row-major LDraw 4x4 per group), color, alpha,
//     width, clip: fn(ctx) to set a clip}
function drawWire(f, o = {}) {
  if (!WIRE) return;
  const cam = camAt(f);
  const xyz = WIRE.xyz, part = WIRE.part, n = WIRE.count;
  const grp = D.parts.group;
  const G = o.groups;
  const sel = o.parts;
  const NB = 4;
  const paths = Array.from({ length: NB }, () => new Path2D());
  // depth range of the model for the fade (near bright, far dim)
  const near = cam.dist * 0.82, far = cam.dist * 1.18;
  for (let i = 0; i < n; i++) {
    const pi = part[i];
    if (sel && !sel.has(pi)) continue;
    let ax = xyz[6 * i], ay = xyz[6 * i + 1], az = xyz[6 * i + 2];
    let bx = xyz[6 * i + 3], by = xyz[6 * i + 4], bz = xyz[6 * i + 5];
    if (G) {
      const g = grp[pi];
      if (g >= 0 && G[g]) {
        const m = G[g];
        const tax = m[0] * ax + m[1] * ay + m[2] * az + m[3];
        const tay = m[4] * ax + m[5] * ay + m[6] * az + m[7];
        const taz = m[8] * ax + m[9] * ay + m[10] * az + m[11];
        const tbx = m[0] * bx + m[1] * by + m[2] * bz + m[3];
        const tby = m[4] * bx + m[5] * by + m[6] * bz + m[7];
        const tbz = m[8] * bx + m[9] * by + m[10] * bz + m[11];
        ax = tax; ay = tay; az = taz; bx = tbx; by = tby; bz = tbz;
      }
    }
    const A = proj(cam, ax, ay, az), B = proj(cam, bx, by, bz);
    if (A[2] <= 0 || B[2] <= 0) continue;
    const d = (A[2] + B[2]) / 2;
    const b = Math.max(0, Math.min(NB - 1, Math.floor((d - near) / (far - near) * NB)));
    paths[b].moveTo(A[0], A[1]); paths[b].lineTo(B[0], B[1]);
  }
  const c = o.ctx || CX;
  c.save();
  if (o.clip) o.clip(c);
  c.globalCompositeOperation = 'lighter';
  c.strokeStyle = o.color || TH.xray;
  c.lineWidth = o.width || 1.1;
  const a0 = o.alpha === undefined ? 0.5 : o.alpha;
  for (let b = 0; b < NB; b++) {
    c.globalAlpha = a0 * lerp(1.0, 0.28, b / (NB - 1));
    c.stroke(paths[b]);
  }
  c.restore();
}

// ------------------------------------------------------------------------------ plates
function segAt(f) {
  const s = D.segments;
  for (let i = 0; i < s.length; i++) if (f >= s[i].start && f < s[i].end) return s[i];
  return s[s.length - 1];
}
function seg(name) { return D.segments.find(s => s.name === name); }
const pad = n => String(n).padStart(5, '0');
// plates are numbered from their segment's start (a shifted edit keeps its renders)
function plateUrl(name, f, variant = null) {
  const dir = D.plates && D.plates[variant ? `${name}@${variant}` : name];
  const sg = seg(name);
  if (!dir || !sg) return null;
  const st = D.plates.step || 1;
  const k = f - sg.start;
  return `${dir}/${pad(k - (((k % st) + st) % st))}.png`;
}
const USED = new Set();                   // plates asked for while drawing this frame
async function plate(name, f, variant = null) {
  const u = plateUrl(name, f, variant);
  if (u) USED.add(u);
  return img(u);
}

// draw a plate full frame (graded for the theme); placeholder when it isn't rendered
function drawPlate(bm, o = {}) {
  const c = o.ctx || CX;
  if (!bm) {
    c.save();
    c.fillStyle = '#C9CDD3'; c.fillRect(0, 0, L, L);
    c.strokeStyle = 'rgba(0,0,0,0.08)'; c.lineWidth = 2;
    for (let i = -L; i < L; i += 60) { c.beginPath(); c.moveTo(i, L); c.lineTo(i + L, 0); c.stroke(); }
    c.restore();
    return;
  }
  c.save();
  const g = TH.grade || {};
  const parts = [];
  if (g.contrast && g.contrast !== 1) parts.push(`contrast(${g.contrast})`);
  if (g.saturate && g.saturate !== 1) parts.push(`saturate(${g.saturate})`);
  if (o.filter) parts.push(o.filter);
  if (parts.length) c.filter = parts.join(' ');
  if (o.dx || o.dy || o.scale) {
    const sc = o.scale || 1;
    c.translate(L / 2 + (o.dx || 0), L / 2 + (o.dy || 0)); c.scale(sc, sc); c.translate(-L / 2, -L / 2);
  }
  c.drawImage(bm, 0, 0, L, L);
  c.filter = 'none';
  if (g.tint && g.amount > 0 && !o.raw) {
    c.globalCompositeOperation = 'soft-light';
    c.globalAlpha = g.amount * 2.2;
    c.fillStyle = g.tint; c.fillRect(0, 0, L, L);
  }
  c.restore();
}

// ------------------------------------------------------------------------------ frame loop
let SHAKE = 0;
function shakeAt(f, frames, amp = 10, len = 9) {
  for (const k of frames) {
    const t = f - k;
    if (t >= 0 && t < len) SHAKE = Math.max(SHAKE, amp * Math.pow(1 - t / len, 2));
  }
}

async function init(size, plan) {
  D = plan;
  TH = D.theme;
  S = size / L;
  CV = document.getElementById('c');
  CV.width = size; CV.height = size;
  CV.style.width = size + 'px'; CV.style.height = size + 'px';
  CX = CV.getContext('2d', { alpha: false });
  await loadFonts();
  await Promise.all([img(D.logo), D.hero ? img(D.hero.url) : null, ...D.thumbs.map(u => img(u))]);
  keyLogo();
  await loadWire();
  makeNoise();
  return true;
}

async function renderFrame(f) {
  F = f;
  const s = segAt(f);
  const drawer = SEG[s.name] || SEG.blank;
  const pre = drawer.prepare ? await drawer.prepare(f, s) : null;
  // plates of transitions' other sides are fetched by the transition itself
  const tpre = await prepareTransitions(f);
  CX.setTransform(1, 0, 0, 1, 0, 0);
  CX.globalCompositeOperation = 'source-over'; CX.globalAlpha = 1; CX.filter = 'none';
  CX.fillStyle = TH.bg; CX.fillRect(0, 0, CV.width, CV.height);
  CX.setTransform(S, 0, 0, S, 0, 0);
  SHAKE = 0;
  if (drawer.shake) drawer.shake(f, s);
  if (SHAKE > 0.01) {                      // shake, scaled up a touch so no edge shows
    const a = hash(f, 7) * Math.PI * 2;
    const k = 1 + 2.4 * SHAKE / L;
    CX.translate(L / 2 + Math.cos(a) * SHAKE, L / 2 + Math.sin(a) * SHAKE);
    CX.scale(k, k); CX.translate(-L / 2, -L / 2);
  }
  drawer.draw(f, s, pre);
  CX.setTransform(S, 0, 0, S, 0, 0);
  drawTransitions(f, tpre);
  post(f, s);
  // keep the plate cache small: plates are used once or twice
  for (const k of Array.from(IMG.keys())) {
    if (k.startsWith('frames/') && !USED.has(k)) {
      const v = IMG.get(k); if (v && v.close) v.close(); IMG.delete(k);
    }
  }
  USED.clear();
  return true;
}

// raw RGBA of the canvas as base64 (fast path to Python)
function grab() {
  const d = CX.getImageData(0, 0, CV.width, CV.height).data;
  return new Promise(res => {
    const fr = new FileReader();
    fr.onload = () => res(fr.result.slice(fr.result.indexOf(',') + 1));
    fr.readAsDataURL(new Blob([d]));
  });
}

window.init = init;
window.renderFrame = renderFrame;
window.grab = grab;
