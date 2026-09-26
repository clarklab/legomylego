/* brickkit showreel compositor: transitions (wipes that cover every cut) and post effects. */
'use strict';

// ------------------------------------------------------------------------------ transitions
// each wipe covers the frame by the cut and uncovers it after: p runs -1 (start) .. 0 (cut,
// fully covered) .. 1 (clear). Quick "band" wipes between build sections don't cover fully.
function activeTransitions(f) {
  return (D.transitions || []).filter(t => Math.abs(f - t.frame) < t.half + (t.type === 'glitch' ? 0 : 1));
}
async function prepareTransitions(f) { return null; }

function drawTransitions(f) {
  for (const t of activeTransitions(f)) {
    const p = clamp((f - t.frame) / t.half, -1, 1);
    const fn = WIPES[t.type] || WIPES.studs;
    CX.save(); fn(f, p, t); CX.restore();
  }
}

const cover = p => (p < 0 ? E.outCubic(clamp(1 + p)) : 1 - E.inCubic(clamp(p)));

const WIPES = {
  // brand: a diagonal wave of studs grows over the frame, then shrinks away
  studs(f, p, t) {
    const cell = 90, rMax = cell * 0.74;
    const col = t.to === 'outro' ? TH.brand.yellow : t.to === 'title' ? TH.brand.red : TH.accent;
    for (let x = cell / 2; x < L + cell; x += cell) for (let y = cell / 2; y < L + cell; y += cell) {
      const d = (x + y) / (2 * L);                 // 0 top-left .. 1 bottom-right
      let q;
      if (p < 0) q = clamp(((1 + p) * 1.6 - d * 0.6) / 1.0);
      else q = 1 - clamp((p * 1.6 - d * 0.6) / 1.0);
      if (q <= 0) continue;
      stud(x, y, rMax * E.outBack(q, 1.3), col);
    }
    if (Math.abs(p) < 0.08) { CX.fillStyle = col; CX.fillRect(0, 0, L, L); }
  },
  // into the build: a wall of bricks slides in row by row, then falls away
  bricks(f, p, t) {
    const rows = 9, bh = L / rows + 1, bw = bh * 2;
    const pal = brickPalette();
    for (let r = 0; r < rows; r++) {
      const y = r * (L / rows);
      const off = (r % 2) * bw / 2;
      const dir = r % 2 ? 1 : -1;
      let dx = 0, dy = 0, a = 1;
      if (p < 0) {
        const q = E.outCubic(clamp((1 + p) * 1.5 - (rows - 1 - r) * 0.06));
        dx = dir * (1 - q) * (L + bw);
        if (q <= 0) continue;
      } else {
        const q = clamp(p * 1.4 - r * 0.045);
        dy = E.inQuad(q) * (L + 200);
        if (q >= 1) continue;
      }
      for (let x = -bw + off; x < L + bw; x += bw) {
        const k = Math.floor((x + 2 * bw) / bw) + r * 7;
        brickFront(x + dx + 2, y + dy + bh * 0.2, bw - 4, bh * 0.8, pal[k % pal.length], 2);
      }
    }
  },
  // between build sections: a quick band that sweeps across on the beat
  band(f, p, t) {
    const th = TH.name;
    if (th === 'tape') { vhsGlitch(f, 1 - Math.abs(p), 0.5); return; }
    if (th === 'scan') {
      const x = lerp(-60, L + 60, (p + 1) / 2);
      CX.save(); CX.globalCompositeOperation = 'screen';
      const g = CX.createLinearGradient(x - 120, 0, x + 20, 0);
      g.addColorStop(0, rgba(TH.xray, 0)); g.addColorStop(0.85, rgba(TH.xray, 0.45)); g.addColorStop(1, rgba(TH.xray, 0));
      CX.fillStyle = g; CX.fillRect(x - 120, 0, 140, L);
      CX.fillStyle = mix(TH.xray, '#ffffff', 0.5); CX.fillRect(x - 1, 0, 3, L);
      CX.restore();
      return;
    }
    // a diagonal band of bricks
    const pal = brickPalette();
    const q = (p + 1) / 2;
    CX.save();
    CX.translate(L / 2, L / 2); CX.rotate(-0.42); CX.translate(-L / 2, -L / 2);
    const bh = 64, bw = 128;
    const cx = lerp(-900, L + 900, E.inOutCubic(q));
    for (let r = 0; r < 3; r++) {
      const y = L / 2 - 1.5 * bh + r * bh;
      for (let i = -6; i < 6; i++) {
        const x = cx + i * bw + (r % 2) * bw / 2 - r * 90;
        brickFront(x, y + bh * 0.2, bw - 4, bh * 0.8, pal[(i + 12 + r * 5) % pal.length], 2);
      }
    }
    CX.restore();
  },
  // sci-fi: blast shutters close from top and bottom with glowing edges, then open
  shutter(f, p, t) {
    const c = cover(p);
    const h = L / 2 * c;
    CX.save();
    CX.fillStyle = TH.bg; CX.fillRect(0, 0, L, h); CX.fillRect(0, L - h, L, h);
    CX.strokeStyle = rgba(TH.accent, 0.12); CX.lineWidth = 1;
    for (let y = 0; y < h; y += 18) { CX.beginPath(); CX.moveTo(0, y); CX.lineTo(L, y); CX.stroke(); }
    for (let y = L - h; y < L; y += 18) { CX.beginPath(); CX.moveTo(0, y); CX.lineTo(L, y); CX.stroke(); }
    CX.shadowColor = TH.accent; CX.shadowBlur = 20; CX.fillStyle = mix(TH.accent, '#ffffff', 0.4);
    CX.fillRect(0, h - 2, L, 3); CX.fillRect(0, L - h - 1, L, 3);
    CX.shadowBlur = 0;
    if (c > 0.85) {
      label(p < 0 ? 'loading' : 'ready', L / 2, L / 2 + 6, { align: 'center', color: TH.hud, size: 22, alpha: clamp((c - 0.85) / 0.15) });
      brackets(L / 2 - 120, L / 2 - 26, L / 2 + 120, L / 2 + 24, 10, rgba(TH.hud, clamp((c - 0.85) / 0.15)), 2);
    }
    CX.restore();
  },
  // tape: the picture tears into noise at the cut
  glitch(f, p, t) {
    const a = 1 - Math.abs(p);
    vhsGlitch(f, a, 1);
    if (a > 0.72) {
      snow(f, clamp((a - 0.72) / 0.28));
    }
  },
  // playful: a panel slides across on the beat, paw prints trotting along its edge
  paws(f, p, t) {
    const tilt = 0.14;
    const e = p < 0 ? E.inOutCubic(clamp(1 + p)) : E.inOutCubic(clamp(p));
    const x0 = p < 0 ? -80 : lerp(-80, L + 160, e);          // trailing edge
    const x1 = p < 0 ? lerp(-80, L + 160, e) : L + 400;       // leading edge
    CX.save();
    CX.translate(L / 2, L / 2); CX.rotate(tilt); CX.translate(-L / 2, -L / 2);
    CX.fillStyle = TH.accent2; CX.fillRect(x0 - 200, -300, Math.max(0, x1 - x0 + 200), L + 600);
    CX.fillStyle = mix(TH.accent2, '#000000', 0.12);
    CX.fillRect(x1 - 26, -300, 26, L + 600);
    // prints along the moving edge, left and right paws in turn
    const ex = p < 0 ? x1 : x0;
    for (let k = 0; k < 7; k++) {
      const y = -40 + k * 175;
      const side = k % 2 ? 1 : -1;
      const px = ex + (p < 0 ? -90 : 90) + side * 22;
      pawPrint(px, y + side * 30, 52, '#FFFFFF', Math.PI / 2, CX, 0.9);
    }
    CX.restore();
  },
};

function brickPalette() {
  const t = TH.name;
  if (t === 'scan') return ['#0B3A46', '#0F5563', '#35F2E0', '#072634', '#18B7FF', '#0A2F3A'];
  if (t === 'tape') return ['#2B0F47', '#FF3EA5', '#1C0B33', '#29E3FF', '#3D1766', '#FFD23F'];
  if (t === 'playful') {
    const P = (D.palette || []).slice(0, 4).map(c => c.rgb);
    return [TH.bg2, TH.accent, TH.accent2, ...P];
  }
  return [TH.brand.yellow, TH.brand.red, TH.brand.black, TH.brand.cream, TH.brand.red, TH.brand.yellow];
}

// ------------------------------------------------------------------------------ VHS artefacts
// slices of the current picture shifted sideways, with colour fringes; a (0..1) is strength
function vhsGlitch(f, a, bands = 1) {
  if (a <= 0) return;
  const [c, x] = off('glitch');
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.drawImage(CV, 0, 0);
  const R = rng(f * 131 + 7);
  const n = Math.floor(6 + 16 * a * bands);
  CX.save();
  CX.setTransform(1, 0, 0, 1, 0, 0);
  for (let i = 0; i < n; i++) {
    const y = R() * CV.height, h = (4 + R() * 60 * a) * S;
    const dx = (R() - 0.5) * 180 * a * S;
    CX.drawImage(c, 0, y, CV.width, h, dx, y, CV.width, h);
    if (R() < 0.5) {
      CX.globalCompositeOperation = 'screen'; CX.globalAlpha = 0.5 * a;
      CX.fillStyle = R() < 0.5 ? TH.accent : TH.accent2;
      CX.fillRect(0, y, CV.width, h * 0.3);
      CX.globalCompositeOperation = 'source-over'; CX.globalAlpha = 1;
    }
  }
  CX.restore();
}
function snow(f, a) {
  if (!NOISE) return;
  CX.save();
  CX.setTransform(1, 0, 0, 1, 0, 0);
  CX.globalAlpha = a;
  const R = rng(f * 17 + 1);
  const ox = Math.floor(R() * 256), oy = Math.floor(R() * 256);
  CX.fillStyle = CX.createPattern(NOISE, 'repeat');
  CX.translate(-ox, -oy);
  CX.fillRect(ox, oy, CV.width, CV.height);
  CX.restore();
  if (a > 0.6) {
    text('TRACKING', L / 2, L / 2 + 16, { font: font(52, 400, 'VT323'), color: '#FFFFFF', align: 'center', spacing: 4, alpha: (a - 0.6) / 0.4, shadow: '#000', sx: 3, sy: 3 });
  }
}

// ------------------------------------------------------------------------------ post
let NOISE = null;
function makeNoise() {
  NOISE = document.createElement('canvas');
  NOISE.width = NOISE.height = 256;
  const x = NOISE.getContext('2d');
  const im = x.createImageData(256, 256);
  const R = rng(12345);
  for (let i = 0; i < 256 * 256; i++) {
    const v = Math.floor(R() * 255);
    im.data[4 * i] = im.data[4 * i + 1] = im.data[4 * i + 2] = v;
    im.data[4 * i + 3] = 255;
  }
  x.putImageData(im, 0, 0);
}

function grain(f, amount) {
  if (!NOISE || amount <= 0) return;
  CX.save();
  CX.setTransform(1, 0, 0, 1, 0, 0);
  const R = rng(f * 7919 + 11);
  const ox = Math.floor(R() * 256), oy = Math.floor(R() * 256);
  CX.globalCompositeOperation = 'overlay';
  CX.globalAlpha = amount;
  const sc = Math.max(1, S * 1.6);          // grain a little coarser than a pixel
  CX.scale(sc, sc);
  CX.fillStyle = CX.createPattern(NOISE, 'repeat');
  CX.translate(-ox, -oy);
  CX.fillRect(ox, oy, CV.width / sc, CV.height / sc);
  CX.restore();
}

function vignette(a) {
  if (a <= 0) return;
  CX.save();
  const g = CX.createRadialGradient(L / 2, L / 2, L * 0.38, L / 2, L / 2, L * 0.78);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  CX.fillStyle = g; CX.fillRect(0, 0, L, L);
  CX.restore();
}

function scanlines(f, a, gap = 3) {
  CX.save();
  CX.fillStyle = `rgba(0,0,0,${a})`;
  for (let y = 0; y < L; y += gap) CX.fillRect(0, y, L, 1);
  // a soft brighter band rolling down
  const y = ((f * 6) % (L + 300)) - 150;
  const g = CX.createLinearGradient(0, y - 120, 0, y + 120);
  g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, `rgba(255,255,255,${a * 0.5})`); g.addColorStop(1, 'rgba(255,255,255,0)');
  CX.globalCompositeOperation = 'screen'; CX.fillStyle = g; CX.fillRect(0, y - 120, L, 240);
  CX.restore();
}

// the tape look: colour channels bleed sideways, scan lines, a head-switching band at the
// bottom, a slow wobble
function vhsLook(f, s) {
  const [c, x] = off('vhs');
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.drawImage(CV, 0, 0);
  const [r, rx] = off('vhs_r');
  rx.setTransform(1, 0, 0, 1, 0, 0);
  rx.drawImage(c, 0, 0);
  rx.globalCompositeOperation = 'multiply'; rx.fillStyle = '#FF0000'; rx.fillRect(0, 0, r.width, r.height);
  const [b, bx] = off('vhs_b');
  bx.setTransform(1, 0, 0, 1, 0, 0);
  bx.drawImage(c, 0, 0);
  bx.globalCompositeOperation = 'multiply'; bx.fillStyle = '#00FFFF'; bx.fillRect(0, 0, b.width, b.height);
  CX.save();
  CX.setTransform(1, 0, 0, 1, 0, 0);
  CX.fillStyle = '#000'; CX.fillRect(0, 0, CV.width, CV.height);
  CX.globalCompositeOperation = 'lighter';
  const d = 2.2 * S;
  CX.filter = `blur(${0.8 * S}px)`;
  CX.drawImage(r, d, 0);
  CX.filter = 'none';
  CX.drawImage(b, -d * 0.6, 0);
  CX.restore();
  scanlines(f, 0.07, 3);
  // head switching noise along the bottom edge
  CX.save(); CX.setTransform(1, 0, 0, 1, 0, 0);
  const hy = CV.height - 10 * S;
  const R = rng(f * 3 + 1);
  for (let k = 0; k < 4; k++) {
    const y = hy + k * 2.5 * S, dx = (R() - 0.3) * 30 * S;
    CX.drawImage(CV, 0, y, CV.width, 2.5 * S, dx, y, CV.width, 2.5 * S);
  }
  CX.restore();
}

function post(f, s) {
  const t = TH.name;
  const isScene = s.kind === 'scene';
  if (t === 'tape') vhsLook(f, s);
  if (t === 'scan' && (isScene || s.name === 'title' || s.name === 'palette')) scanlines(f, 0.05, 3);
  vignette(t === 'brand' ? 0.1 : t === 'playful' ? 0.08 : 0.3);
  grain(f, TH.grain || 0);
}
