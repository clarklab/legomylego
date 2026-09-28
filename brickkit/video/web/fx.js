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
    if (th === 'grindhouse') { frameSlip(f, p, t, 0.16); return; }
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
  // grindhouse: the print catches in the gate and burns - a blister of white-hot emulsion with
  // a charred rim eats the picture, the cut is spliced in with a slip and a flash, the burn clears
  burn(f, p, t) {
    const R = rng(t.frame * 97 + 13);
    const a0 = R() * Math.PI * 2;
    const ox = L / 2 + Math.cos(a0) * L * 0.2, oy = L / 2 + Math.sin(a0) * L * 0.2;
    const ph = [0, 0, 1, 2, 3, 4, 5].map(() => R() * Math.PI * 2);
    // the hole grows from a spot, slowly then all at once; after the cut the light clears
    const q = p < 0 ? clamp(1 + p) : clamp(1 - p);
    const c = p < 0 ? Math.pow(q, 2.2) : Math.pow(q, 1.6);
    // the picture over-exposes towards amber as the burn takes hold
    CX.save();
    CX.globalCompositeOperation = 'screen';
    CX.fillStyle = rgba('#FF8A2A', 0.45 * q * q * q * (0.85 + 0.3 * hash(f, 91)));
    CX.fillRect(0, 0, L, L);
    CX.restore();
    if (p > 0) frameSlip(f, p * 0.6, t, 0.12);           // spliced in: settles as it clears
    if (c < 0.003) return;
    const rad = c * L * 1.3;
    const edge = (a, k) => rad * k * (1 + 0.16 * (Math.sin(2 * a + ph[1] + f * 0.07)
      + Math.sin(3 * a + ph[2] - f * 0.05) / 2 + Math.sin(5 * a + ph[3] + f * 0.11) / 3
      + Math.sin(7 * a + ph[4]) / 4 + Math.sin(11 * a + ph[5] - f * 0.13) / 5));
    const blob = (k, grow = 0) => {
      CX.beginPath();
      for (let i = 0; i <= 96; i++) {
        const a = i / 96 * Math.PI * 2;
        const r = edge(a, k) + grow;
        if (i === 0) CX.moveTo(ox + Math.cos(a) * r, oy + Math.sin(a) * r);
        else CX.lineTo(ox + Math.cos(a) * r, oy + Math.sin(a) * r);
      }
      CX.closePath();
    };
    CX.save();
    CX.globalAlpha = p > 0 ? Math.min(1, q * 1.6) : 1;
    // a charred rim, then the molten orange, then the white-hot hole
    CX.filter = `blur(${10 * S}px)`;
    CX.fillStyle = rgba('#1C0A03', 0.85); blob(1.0, 26); CX.fill();
    CX.filter = `blur(${4 * S}px)`;
    const g = CX.createRadialGradient(ox, oy, 0, ox, oy, Math.max(1, rad * 1.1));
    g.addColorStop(0, '#FFF8EA'); g.addColorStop(0.5, '#FFE3A6'); g.addColorStop(0.78, '#FFA23A');
    g.addColorStop(0.93, '#E4460E'); g.addColorStop(1, '#6B1604');
    CX.fillStyle = g; blob(1.0); CX.fill();
    CX.filter = 'none';
    // blisters bubbling up ahead of the edge
    CX.filter = `blur(${2.5 * S}px)`;
    for (let i = 0; i < 9; i++) {
      const a = R() * Math.PI * 2, k = 1.06 + R() * 0.25, s = (4 + R() * 16) * clamp(c * 4);
      const r = edge(a, k);
      const x = ox + Math.cos(a) * r, y = oy + Math.sin(a) * r, sq = 0.6 + 0.4 * R(), rot = R() * Math.PI;
      CX.fillStyle = rgba('#2A0E04', 0.75); CX.beginPath(); CX.ellipse(x, y, s + 4, (s + 4) * sq, rot, 0, Math.PI * 2); CX.fill();
      CX.fillStyle = rgba('#FFB347', 0.95); CX.beginPath(); CX.ellipse(x, y, s, s * sq, rot, 0, Math.PI * 2); CX.fill();
      CX.fillStyle = rgba('#FFF4DC', 0.9); CX.beginPath(); CX.ellipse(x, y, s * 0.45, s * 0.45 * sq, rot, 0, Math.PI * 2); CX.fill();
    }
    CX.filter = 'none';
    CX.restore();
    // at the cut the gate is all light
    if (Math.abs(p) < 0.12) { CX.fillStyle = '#FFF6E6'; CX.fillRect(0, 0, L, L); }
  },
};

// grindhouse: the film slips a frame in the gate - the picture jumps by `amt` of a frame, the
// frame line and the sprocket holes show, the lamp flares; |p| < 1 is the slip's span
function frameSlip(f, p, t, amt) {
  const q = 1 - Math.abs(p);
  if (q <= 0) return;
  const dir = hash(t.frame, 5) < 0.5 ? 1 : -1;
  const jolt = q > 0.62 ? 1 : q > 0.45 ? 0.4 : 0;          // it jumps, hangs, then catches
  const dy = dir * jolt * amt * L * (0.85 + 0.3 * hash(f, 6));
  if (Math.abs(dy) > 0.5) {
    const [c, x] = off('slip');
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.drawImage(CV, 0, 0);
    const gap = 22;                                        // the black frame line
    CX.save();
    CX.fillStyle = '#050302'; CX.fillRect(0, 0, L, L);
    CX.drawImage(c, 0, dy, L, L);
    CX.drawImage(c, 0, dy - dir * (L + gap), L, L);       // the neighbouring frame
    const ly = dy > 0 ? dy - gap : dy + L;
    CX.fillStyle = '#050302'; CX.fillRect(0, ly, L, gap);
    // the film's edge: sprocket holes passing the gate
    CX.fillStyle = rgba('#050302', 0.9); CX.fillRect(0, 0, 46, L);
    CX.fillStyle = rgba('#F4E6C8', 0.85);
    const pitch = (L + gap) / 2;
    for (let y = ((dy % pitch) + pitch) % pitch - pitch; y < L; y += pitch) {
      rrect(10, y + pitch / 2 - 30, 24, 60, 6); CX.fill();
    }
    CX.restore();
  }
  // the lamp flares as the frame jumps
  const fl = q > 0.7 ? (q - 0.7) / 0.3 * (0.35 + 0.35 * hash(f, 8)) : 0.08 * q * hash(f, 9);
  if (fl > 0.01) {
    CX.save(); CX.globalCompositeOperation = 'screen';
    CX.fillStyle = rgba('#FFF1D8', fl); CX.fillRect(0, 0, L, L);
    CX.restore();
  }
}

function brickPalette() {
  const t = TH.name;
  if (t === 'scan') return ['#0B3A46', '#0F5563', '#35F2E0', '#072634', '#18B7FF', '#0A2F3A'];
  if (t === 'tape') return ['#2B0F47', '#FF3EA5', '#1C0B33', '#29E3FF', '#3D1766', '#FFD23F'];
  if (t === 'grindhouse') return ['#2B2019', TH.accent, '#4A3A2E', TH.accent2, '#1A120E', TH.ink];
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
    text('TRACKING', L / 2, L / 2 + 16, { font: font(52, 400, VCR), color: '#FFFFFF', align: 'center', spacing: 4, alpha: (a - 0.6) / 0.4, shadow: '#000', sx: 3, sy: 3 });
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

function vignette(a, r0 = 0.38, r1 = 0.78) {
  if (a <= 0) return;
  CX.save();
  const g = CX.createRadialGradient(L / 2, L / 2, L * r0, L / 2, L / 2, L * r1);
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

// the grindhouse print: gate weave, a faded warm stock, exposure flicker, dust, hairs and
// scratches that come and go, now and then a light leak, a heavy soft vignette. The artefacts
// are frame-seeded (deterministic) and kept small and off the middle while the model builds.
function filmLook(f, s) {
  const build = s.name === 'build';
  // gate weave: the whole picture wanders a pixel or so (scaled a touch so no edge shows)
  const wx = (hash(f, 11) - 0.5) * 1.4 + Math.sin(f * 0.23) * 0.5;
  const wy = (hash(f, 12) - 0.5) * 2.0 + Math.sin(f * 0.11 + 1.3) * 0.9;
  const [c, x] = off('weave');
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.drawImage(CV, 0, 0);
  CX.save();
  CX.setTransform(1, 0, 0, 1, 0, 0);
  const k = 1.008;
  CX.translate(CV.width / 2 + wx * S, CV.height / 2 + wy * S); CX.scale(k, k);
  CX.translate(-CV.width / 2, -CV.height / 2);
  CX.drawImage(c, 0, 0);
  CX.restore();
  CX.save();
  // the stock: whites a little warm, blacks lifted to a brown
  CX.globalCompositeOperation = 'multiply'; CX.fillStyle = '#FFF0D8'; CX.fillRect(0, 0, L, L);
  CX.globalCompositeOperation = 'screen'; CX.fillStyle = '#140B06'; CX.fillRect(0, 0, L, L);
  // exposure flicker
  const fl = (hash(f, 13) - 0.5) * 0.08 + Math.sin(f * 0.61) * 0.015;
  if (fl > 0) { CX.globalCompositeOperation = 'screen'; CX.fillStyle = rgba('#FFE9C8', fl); }
  else { CX.globalCompositeOperation = 'source-over'; CX.fillStyle = rgba('#000000', -fl); }
  CX.fillRect(0, 0, L, L);
  CX.globalCompositeOperation = 'source-over';
  // dust: specks for a frame each, mostly dark, sometimes a bright one
  const R = rng(f * 7919 + 3);
  const n = Math.floor(R() * (build ? 4 : 7));
  for (let i = 0; i < n; i++) {
    const px = R() * L, py = R() * L, big = R() < 0.12, sz = big ? 3 + R() * 5 : 0.8 + R() * 2.2;
    if (build && Math.hypot(px - L / 2, py - L / 2) < L * 0.3 && sz > 2) continue;
    CX.fillStyle = R() < 0.75 ? rgba('#0C0604', 0.55 + 0.35 * R()) : rgba('#FFF4DE', 0.45 + 0.3 * R());
    CX.beginPath(); CX.ellipse(px, py, sz, sz * (0.5 + 0.5 * R()), R() * Math.PI, 0, Math.PI * 2); CX.fill();
    if (big) { CX.beginPath(); CX.ellipse(px + sz * 0.8, py + sz * 0.3, sz * 0.5, sz * 0.4, 0, 0, Math.PI * 2); CX.fill(); }
  }
  // a hair caught in the gate: stays a few frames near an edge, trembling
  const hw = Math.floor(f / 41), hr = rng(hw * 31 + 7);
  if (hr() < 0.35) {
    const h0 = hw * 41 + Math.floor(hr() * 20), h1 = h0 + 6 + Math.floor(hr() * 14);
    if (f >= h0 && f < h1) {
      const side = Math.floor(hr() * 4), along = 0.15 + hr() * 0.7, depth = 20 + hr() * 90;
      let hx = side < 2 ? along * L : side === 2 ? depth : L - depth;
      let hy = side < 2 ? (side === 0 ? depth : L - depth) : along * L;
      hx += (hash(f, 14) - 0.5) * 3; hy += (hash(f, 15) - 0.5) * 3;
      const len = 40 + hr() * 90, a = hr() * Math.PI * 2;
      CX.strokeStyle = rgba('#0A0503', 0.7); CX.lineWidth = 1.3; CX.lineCap = 'round';
      CX.beginPath(); CX.moveTo(hx, hy);
      CX.bezierCurveTo(hx + Math.cos(a) * len * 0.4 + 20, hy + Math.sin(a) * len * 0.4 - 15,
        hx + Math.cos(a + 0.8) * len * 0.8, hy + Math.sin(a + 0.8) * len * 0.8,
        hx + Math.cos(a + 0.4) * len, hy + Math.sin(a + 0.4) * len);
      CX.stroke();
    }
  }
  // scratches: fine vertical lines that run for a second or so, drifting, flickering
  for (let lane = 0; lane < 2; lane++) {
    const W = 29 + lane * 17, w = Math.floor(f / W), sr = rng(w * 131 + lane * 977 + 5);
    if (sr() > (build ? 0.4 : 0.55)) continue;
    const sx = (0.08 + sr() * 0.84) * L + (f - w * W) * (sr() - 0.5) * 1.2;
    if (build && Math.abs(sx - L / 2) < L * 0.18) continue;
    const bright = sr() < 0.6;
    CX.fillStyle = bright ? rgba('#FFF4DE', 0.12 + 0.18 * hash(f, 16 + lane))
      : rgba('#0C0604', 0.2 + 0.2 * hash(f, 18 + lane));
    let y = -20;
    while (y < L) {                                   // broken where the emulsion held
      const seg = 80 + sr() * 400;
      CX.fillRect(sx + Math.sin(y * 0.01 + w) * 1.5, y, 1.4, seg);
      y += seg + sr() * 60;
    }
  }
  // a light leak now and then: warm flare bleeding in from an edge
  const lw = Math.floor(f / 97), lr = rng(lw * 57 + 11);
  if (lr() < 0.4) {
    const l0 = lw * 97 + Math.floor(lr() * 60), l1 = l0 + 22 + Math.floor(lr() * 14);
    if (f >= l0 && f < l1) {
      const u = (f - l0) / (l1 - l0);
      const amp = Math.sin(Math.PI * u) * (0.75 + 0.25 * hash(f, 19)) * (build || s.kind === 'scene' ? 0.2 : 0.42);
      const side = Math.floor(lr() * 3), cx = side === 0 ? -80 : side === 1 ? L + 80 : lr() * L;
      const cy = side === 2 ? -80 : (0.2 + lr() * 0.6) * L;
      const g = CX.createRadialGradient(cx, cy, 10, cx, cy, L * 0.62);
      g.addColorStop(0, rgba('#FFD08A', amp)); g.addColorStop(0.35, rgba('#FF6A1A', amp * 0.8));
      g.addColorStop(1, rgba('#B01A00', 0));
      CX.globalCompositeOperation = 'screen'; CX.fillStyle = g; CX.fillRect(0, 0, L, L);
    }
  }
  CX.restore();
  vignette(0.62, 0.26, 0.86);
}

function post(f, s) {
  if (s.name === 'cold_open' && f >= D.cold_open.cut) return;      // the hard cut: black
  const t = TH.name;
  const isScene = s.kind === 'scene';
  if (t === 'tape') vhsLook(f, s);
  if (t === 'scan' && (isScene || s.name === 'title' || s.name === 'palette')) scanlines(f, 0.05, 3);
  if (t === 'grindhouse') filmLook(f, s);
  else vignette(t === 'brand' ? 0.1 : t === 'playful' ? 0.08 : 0.3);
  grain(f, TH.grain || 0);
}
