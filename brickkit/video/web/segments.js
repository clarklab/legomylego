/* brickkit showreel compositor: one drawer per segment (see reel.py for the plan). */
'use strict';

const SEG = {};
const B = () => D.beat;
const UP = s => String(s).toUpperCase();
const TOPY = () => (TH.name === 'tape' ? 176 : 96);      // first header line, clear of the OSD
const fmt = n => Math.round(n).toLocaleString('en-US');

// ------------------------------------------------------------------------------ theme skins
function background(f) {
  const t = TH.name;
  CX.save();
  if (t === 'scan') {
    const g = CX.createRadialGradient(L / 2, L * 0.46, 40, L / 2, L / 2, L * 0.78);
    g.addColorStop(0, TH.bg2); g.addColorStop(1, TH.bg);
    CX.fillStyle = g; CX.fillRect(0, 0, L, L);
    CX.strokeStyle = rgba(TH.accent, 0.05); CX.lineWidth = 1;
    for (let x = 0; x <= L; x += 54) { CX.beginPath(); CX.moveTo(x, 0); CX.lineTo(x, L); CX.stroke(); }
    for (let y = 0; y <= L; y += 54) { CX.beginPath(); CX.moveTo(0, y); CX.lineTo(L, y); CX.stroke(); }
    CX.strokeStyle = rgba(TH.accent, 0.22);
    for (let x = 54; x < L; x += 162) for (let y = 54; y < L; y += 162) {
      CX.beginPath(); CX.moveTo(x - 5, y); CX.lineTo(x + 5, y); CX.moveTo(x, y - 5); CX.lineTo(x, y + 5); CX.stroke();
    }
  } else if (t === 'tape') {
    const g = CX.createLinearGradient(0, 0, 0, L);
    g.addColorStop(0, TH.bg); g.addColorStop(0.62, TH.bg2); g.addColorStop(1, TH.bg);
    CX.fillStyle = g; CX.fillRect(0, 0, L, L);
    // a perspective floor grid rolling towards us
    const hz = L * 0.64, vx = L / 2;
    CX.save();
    CX.beginPath(); CX.rect(0, hz, L, L - hz); CX.clip();
    CX.strokeStyle = rgba(TH.accent, 0.34); CX.lineWidth = 1.5;
    for (let i = -14; i <= 14; i++) {
      CX.beginPath(); CX.moveTo(vx + i * 16, hz); CX.lineTo(vx + i * 150, L); CX.stroke();
    }
    const ph = (f / 20) % 1;
    for (let k = 0; k < 14; k++) {
      const z = (k + 1 - ph);
      const y = hz + (L - hz) * Math.pow(z / 14, 2.2);
      CX.globalAlpha = clamp(z / 3);
      CX.beginPath(); CX.moveTo(0, y); CX.lineTo(L, y); CX.stroke();
    }
    CX.restore();
    const hg = CX.createLinearGradient(0, hz - 60, 0, hz + 20);
    hg.addColorStop(0, rgba(TH.accent, 0)); hg.addColorStop(0.75, rgba(TH.accent, 0.28)); hg.addColorStop(1, rgba(TH.accent2, 0));
    CX.fillStyle = hg; CX.fillRect(0, hz - 60, L, 80);
  } else if (t === 'playful') {
    CX.fillStyle = TH.bg; CX.fillRect(0, 0, L, L);
    // a faint trail of paw prints walking diagonally across, drifting slowly
    const drift = (f * 0.6) % 180;
    for (let row = -2; row < 9; row++) for (let k = 0; k < 8; k++) {
      const x = -120 + k * 180 + (row % 2) * 90 + drift;
      const y = row * 150 + (k % 2) * 34 - drift * 0.55;
      pawPrint(x, y, 34, TH.accent2, -0.5, CX, 0.1);
    }
  } else {
    CX.fillStyle = TH.bg; CX.fillRect(0, 0, L, L);
    CX.fillStyle = rgba(TH.ink, 0.045);
    for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) { circle(x, y, 11); CX.fill(); }
  }
  CX.restore();
}

// small uppercase label
function label(str, x, y, o = {}) {
  const mono = TH.mono;
  const size = o.size || (mono === 'VT323' ? 32 : 22);
  text(mono === 'Fredoka' ? str : UP(str), x, y, {
    font: monoFont(size), spacing: mono === 'VT323' ? 1 : size * 0.14, color: o.color || TH.muted,
    align: o.align, alpha: o.alpha, base: o.base, shadow: o.shadow, blur: o.blur, ctx: o.ctx,
  });
}

// a panel behind HUD text, in the theme's style
function panel(x, y, w, h, o = {}) {
  const a = o.alpha === undefined ? 1 : o.alpha;
  if (a <= 0) return;
  CX.save(); CX.globalAlpha = a;
  const t = TH.name;
  if (t === 'scan') {
    CX.fillStyle = TH.panel; CX.fillRect(x, y, w, h);
    CX.strokeStyle = rgba(TH.hud, 0.35); CX.lineWidth = 1; CX.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    brackets(x - 4, y - 4, x + w + 4, y + h + 4, 16, TH.hud, 2.5);
  } else if (t === 'tape') {
    CX.fillStyle = TH.panel; CX.fillRect(x, y, w, h);
    CX.fillStyle = rgba(TH.accent, 0.9); CX.fillRect(x, y, 6, h);
  } else if (t === 'playful') {
    CX.fillStyle = rgba('#000000', 0.12); rrect(x + 6, y + 8, w, h, 26); CX.fill();
    CX.fillStyle = TH.panel; rrect(x, y, w, h, 26); CX.fill();
    CX.strokeStyle = TH.ink; CX.lineWidth = 3.5; rrect(x, y, w, h, 26); CX.stroke();
  } else {
    CX.fillStyle = TH.panel; rrect(x, y, w, h, 18); CX.fill();
    CX.strokeStyle = TH.ink; CX.lineWidth = 3; rrect(x, y, w, h, 18); CX.stroke();
  }
  CX.restore();
}

// status icon: pass (check), warn (!), fail (x), na (dash); p = draw-on progress
function statusIcon(x, y, r, st, p, na = false) {
  const col = na ? TH.muted : st === 'pass' ? TH.ok : st === 'warn' ? TH.warn : TH.accent;
  const sc = E.spring(clamp(p * 1.6), 2.0, 7);
  if (sc <= 0) return;
  CX.save(); CX.translate(x, y); CX.scale(sc, sc);
  if (TH.name === 'scan' || TH.name === 'tape') {
    CX.strokeStyle = col; CX.lineWidth = 2.5; circle(0, 0, r); CX.stroke();
    CX.fillStyle = rgba(col, 0.16); circle(0, 0, r); CX.fill();
  } else {
    CX.fillStyle = col; circle(0, 0, r); CX.fill();
  }
  const ink = (TH.name === 'scan' || TH.name === 'tape') ? col : '#FFFFFF';
  if (na) {
    CX.strokeStyle = ink; CX.lineWidth = r * 0.22; CX.lineCap = 'round';
    CX.beginPath(); CX.moveTo(-r * 0.4, 0); CX.lineTo(r * 0.4, 0); CX.stroke();
  } else if (st === 'pass') {
    checkMark(0, 0, r * 1.25, ink, clamp(p * 2 - 0.3), r * 0.24);
  } else if (st === 'warn') {
    CX.fillStyle = ink; CX.font = font(r * 1.5, 700); CX.textAlign = 'center'; CX.textBaseline = 'middle';
    CX.fillText('!', 0, r * 0.08);
  } else {
    CX.strokeStyle = ink; CX.lineWidth = r * 0.22; CX.lineCap = 'round';
    CX.beginPath(); CX.moveTo(-r * 0.36, -r * 0.36); CX.lineTo(r * 0.36, r * 0.36);
    CX.moveTo(r * 0.36, -r * 0.36); CX.lineTo(-r * 0.36, r * 0.36); CX.stroke();
  }
  CX.restore();
}

// a stat chip: bold value + label; returns its width. p: 0..1 appear
function chip(value, lab, x, y, p, k = 0, o = {}) {
  const t = TH.name;
  const h = o.h || 62;
  const vs = value ? (o.vsize || 32) : 0, ls = o.lsize || (TH.mono === 'VT323' ? 36 : 21);
  const vfont = font(vs, 700);
  const lfont = monoFont(ls);
  const lab2 = TH.mono === 'Fredoka' ? lab : UP(lab);
  const vw = value ? measure(value, vfont) : 0;
  const lw = measure(lab2, lfont, TH.mono === 'VT323' ? 1 : ls * 0.1);
  const gap = value ? 12 : 0;
  const w = vw + gap + lw + 44;
  if (p <= 0) return w;
  const sc = t === 'playful' ? E.spring(p, 1.8, 6) : E.outBack(clamp(p), 2.2);
  CX.save();
  CX.translate(x + w / 2, y + h / 2); CX.scale(sc, sc); CX.translate(-w / 2, -h / 2);
  CX.globalAlpha = clamp(p * 3);
  let fg = TH.hud_ink, lc = TH.hud_ink;
  if (t === 'scan') {
    CX.fillStyle = rgba(TH.bg, 0.72); CX.fillRect(0, 0, w, h);
    CX.strokeStyle = rgba(TH.hud, 0.55); CX.lineWidth = 1.5; CX.strokeRect(0.75, 0.75, w - 1.5, h - 1.5);
    brackets(-3, -3, w + 3, h + 3, 10, TH.hud, 2);
    fg = TH.ink; lc = TH.hud;
  } else if (t === 'tape') {
    CX.fillStyle = rgba('#000000', 0.55); CX.fillRect(0, 0, w, h);
    CX.strokeStyle = rgba(k % 2 ? TH.accent2 : TH.accent, 0.9); CX.lineWidth = 2; CX.strokeRect(1, 1, w - 2, h - 2);
    fg = TH.ink; lc = mix(k % 2 ? TH.accent2 : TH.accent, '#ffffff', 0.4);
  } else if (t === 'playful') {
    const cols = [TH.accent, TH.accent2, '#2BB673', '#3D7DFF', TH.bg2];
    const col = cols[k % cols.length];
    CX.fillStyle = rgba('#000000', 0.14); rrect(4, 6, w, h, h / 2); CX.fill();
    CX.fillStyle = col; rrect(0, 0, w, h, h / 2); CX.fill();
    fg = onColour(col); lc = fg;
  } else {
    CX.fillStyle = TH.ink; rrect(0, 0, w, h, h / 2); CX.fill();
    fg = TH.bg2; lc = TH.bg;
  }
  const by = h / 2 + vs * 0.35;
  if (value) text(value, 22, by, { font: vfont, color: fg });
  text(lab2, 22 + vw + gap, h / 2 + ls * 0.36, { font: lfont, color: lc,
    spacing: TH.mono === 'VT323' ? 1 : ls * 0.1, alpha: 0.92 });
  CX.restore();
  return w;
}

// an odometer: the digits of `n` roll into place; returns width
function odometer(n, x, y, size, p, o = {}) {
  const str = fmt(n);
  const fnt = font(size, 700);
  const g = glyphs(str, fnt, -size * 0.02);
  const digitH = size * 1.05;
  CX.save();
  CX.beginPath(); CX.rect(x - 10, y - size * 0.95, g.width + 20, size * 1.18); CX.clip();
  const digits = str.replace(/,/g, '').length;
  let di = 0;
  g.list.forEach((gl, i) => {
    if (gl.ch === ',') {
      text(',', x + gl.x, y, { font: fnt, color: o.color, alpha: clamp(p * 4) });
      return;
    }
    const target = parseInt(gl.ch, 10);
    const place = digits - di - 1;
    di++;
    // higher places settle first; each digit spins through 10 * (2 + place) steps
    const q = E.outQuint(clamp(p * (1 + place * 0.12)));
    const spins = 10 * (1 + Math.min(place, 3)) + target;
    const v = spins * q;
    const base = Math.floor(v), frac = v - base;
    for (let k = 0; k < 2; k++) {
      const d = (base + k) % 10;
      const yy = y - frac * digitH + k * digitH;
      const blur = (1 - q) > 0.05 ? 0.55 : 1;
      text(String(d), x + gl.x + gl.w / 2, yy, { font: fnt, color: o.color, align: 'center', alpha: blur * (k === 0 ? 1 - frac * 0.6 : 0.4 + frac * 0.6) });
    }
  });
  CX.restore();
  return g.width;
}

// the TV-style on-screen display for the tape theme
function osd(f, s, state) {
  if (TH.name !== 'tape') return;
  const size = 44;
  const o = { font: font(size, 400, 'VT323'), color: TH.ink, shadow: rgba('#000000', 0.8), sx: 3, sy: 3, spacing: 2 };
  if (state) text(state, M, M + 30, o);
  text('SP', L - M, M + 30, Object.assign({}, o, { align: 'right' }));
  const t = Math.floor(f / D.fps);
  const tc = `${Math.floor(t / 3600)}:${String(Math.floor(t / 60) % 60).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
  text(tc, L - M, L - M + 6, Object.assign({}, o, { align: 'right', font: font(38, 400, 'VT323') }));
}

// the sci-fi visor frame for the scan theme: corner brackets and live camera telemetry
function visor(f, s, title) {
  if (TH.name !== 'scan') return;
  brackets(34, 34, L - 34, L - 34, 46, rgba(TH.hud, 0.8), 2);
  const C = D.camera;
  const k = Math.max(0, Math.min(C.pos.length - 1, f - C.start));
  const az = C.az ? ((C.az[k] % 360) + 360) % 360 : 0, el = C.el ? C.el[k] : 0;
  label(`AZ ${az.toFixed(1).padStart(5, '0')}°  EL ${el.toFixed(1)}°`, L - 52, L - 50,
    { align: 'right', color: rgba(TH.hud, 0.75), size: 18 });
  label(title || '', 52, L - 50, { color: rgba(TH.hud, 0.75), size: 18 });
}

// ------------------------------------------------------------------------------ open
SEG.open = {
  shake(f) {
    const m = D.marks.open;
    shakeAt(f, [m.land], 14, 10);
    shakeAt(f, m.words, 6, 6);
  },
  draw(f, s) {
    const m = D.marks.open, b = B();
    const Y = TH.brand.yellow, R = TH.brand.red, K = TH.brand.black, CR = TH.brand.cream;
    CX.fillStyle = K; CX.fillRect(0, 0, L, L);
    // faint studs on the dark stage
    for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 13, '#1C1B1A');
    const cx0 = L / 2, cy0 = L / 2 + 10;
    // the yellow stud wave from the landing brick
    const wp = ramp(f, m.wipe, m.wipe_end);
    if (wp > 0) {
      const cell = 60, rMax = cell * 0.76, spread = 900;
      for (let x = 30; x < L; x += cell) for (let y = 30; y < L; y += cell) {
        const d = Math.hypot(x - cx0, y - cy0) / spread;
        const q = clamp((wp * 1.35 - d * 0.9) / 0.35);
        if (q <= 0) continue;
        const r = rMax * E.outBack(q, 1.6);
        stud(x, y, Math.min(r, rMax * 1.08), Y);
      }
      if (wp >= 1) {
        CX.fillStyle = Y; CX.fillRect(0, 0, L, L);
        for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 20, mix(Y, '#ffffff', 0.08), CX, 0.55);
      }
    }
    // the brick: falls towards us, lands, squashes; shrinks away as the words arrive
    const dp = ramp(f, m.drop, m.land);
    const gone = tw(f, m.words[0] - 5, m.words[0] + 3, E.inBack);
    if (dp > 0 && gone < 1) {
      const k = f - m.land;
      let sc = lerp(3.4, 1, E.inQuad(dp));
      let sx = 1, sy = 1;
      if (k >= 0) { const w = Math.exp(-k / 3.2) * Math.cos(k * 1.1); sx = 1 + 0.12 * w; sy = 1 - 0.12 * w; }
      sc *= 1 - gone;
      CX.save();
      CX.globalAlpha = clamp(dp * 4);
      // shadow tightening under it
      CX.fillStyle = rgba('#000000', 0.45 * clamp(dp * 1.5));
      CX.filter = `blur(${lerp(40, 10, dp) * S}px)`;
      CX.beginPath(); CX.ellipse(cx0 + 10, cy0 + 26, 150 * sc, 86 * sc, 0, 0, Math.PI * 2); CX.fill();
      CX.filter = 'none';
      CX.translate(cx0, cy0); CX.scale(sc * sx, sc * sy);
      brickTop(0, 0, 4, 2, 66, R);
      CX.restore();
    }
    // impact: a shock ring and sparks
    const k = f - m.land;
    if (k >= 0 && k < 14) {
      const q = k / 14;
      CX.save();
      CX.strokeStyle = rgba(CR, 1 - q); CX.lineWidth = 10 * (1 - q) + 1;
      circle(cx0, cy0, 170 + 260 * E.outCubic(q)); CX.stroke();
      CX.strokeStyle = rgba(Y, 1 - q); CX.lineWidth = 7; CX.lineCap = 'round';
      for (let i = 0; i < 10; i++) {
        const a = i / 10 * Math.PI * 2 + 0.3;
        const r0 = 190 + 170 * E.outCubic(q), r1 = r0 + 60 * (1 - q);
        CX.beginPath(); CX.moveTo(cx0 + Math.cos(a) * r0, cy0 + Math.sin(a) * r0 * 0.9);
        CX.lineTo(cx0 + Math.cos(a) * r1, cy0 + Math.sin(a) * r1 * 0.9); CX.stroke();
      }
      CX.restore();
    }
    // REAL LEGO / PIECES. slam in word by word
    const words = [['REAL', 0], ['LEGO', 0], ['PIECES.', 1]];
    const size = Math.min(210, fitSize('REAL LEGO', 210, 930, 700, null, -0.02));
    const fnt = font(size, 700);
    const line0 = measure('REAL LEGO', fnt, -4);
    const sp = measure(' ', fnt);
    const wx = [L / 2 - line0 / 2, L / 2 - line0 / 2 + measure('REAL', fnt, -4) + sp, L / 2 - measure('PIECES.', fnt, -4) / 2];
    const wy = [470, 470, 470 + size * 0.95];
    words.forEach(([w, _], i) => {
      const t0 = m.words[i];
      const q = ramp(f, t0, t0 + 7);
      if (q <= 0) return;
      const sc = 2.3 - 1.3 * E.outBack(q, 2.6);
      const ww = measure(w, fnt, -4);
      const gx = wx[i] + ww / 2, gy = wy[i] - size * 0.35;
      for (let g = 2; g >= 0; g--) {            // motion smear while it's fast
        const ghost = g > 0 ? clamp(1 - q * 3) * 0.18 : clamp(q * 4);
        if (ghost <= 0.005) continue;
        CX.save();
        CX.translate(gx, gy); CX.scale(sc * (1 + g * 0.18), sc * (1 + g * 0.18)); CX.rotate((1 - E.outCubic(q)) * -0.12);
        text(w, -ww / 2, size * 0.35, { font: fnt, color: K, alpha: ghost, spacing: -4 });
        CX.restore();
      }
    });
    // CHECKED BY COMPUTER. on a black band that wipes in
    const bp = ramp(f, m.band, m.band + 8);
    if (bp > 0) {
      const bw = 760, bh = 96, bx = L / 2 - bw / 2, by = 740;
      const e = E.outExpo(bp);
      CX.save();
      CX.beginPath(); CX.rect(bx, by - 6, bw * e, bh + 12); CX.clip();
      CX.fillStyle = K; rrect(bx, by, bw, bh, 14); CX.fill();
      CX.fillStyle = R; circle(bx + 58, by + bh / 2, 28); CX.fill();
      checkMark(bx + 58, by + bh / 2, 36, CR, tw(f, m.band + 4, m.band + 12), 7);
      const ts = fitSize('CHECKED BY COMPUTER.', 50, bw - 130, 700);
      text('CHECKED BY COMPUTER.', bx + 106, by + bh / 2 + ts * 0.36, { size: ts, color: Y,
        alpha: tw(f, m.band + 2, m.band + 8) });
      CX.restore();
    }
  },
};

// ------------------------------------------------------------------------------ title
function heroRect(top = 262) {
  const H = D.hero;
  const [x0, y0, x1, y1] = H.box;
  const region = H.cutout ? [90, top, 990, 846] : [170, top + 10, 910, 836];
  const bw = (x1 - x0), bh = (y1 - y0);
  const sc = Math.min((region[2] - region[0]) / bw, (region[3] - region[1]) / bh);
  const w = sc, h = sc;                       // the whole image drawn w x h
  const cx = (region[0] + region[2]) / 2, cy = (region[1] + region[3]) / 2;
  return { x: cx - (x0 + bw / 2) * w, y: cy - (y0 + bh / 2) * h, w, h, box: [cx - bw * sc / 2, cy - bh * sc / 2, cx + bw * sc / 2, cy + bh * sc / 2] };
}

function nameLines(name, maxW, size) {
  const up = UP(name);
  const one = measure(up, font(size, 700), -size * 0.02);
  if (one * 104 / size <= maxW || !up.includes(' ')) return [up];   // one line if it fits at 104px
  const words = up.split(' ');
  let best = null;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(' '), b = words.slice(i).join(' ');
    const w = Math.max(measure(a, font(size, 700)), measure(b, font(size, 700)));
    if (!best || w < best[0]) best = [w, [a, b]];
  }
  return best[1];
}

SEG.title = {
  draw(f, s) {
    const m = D.marks.title, b = B();
    background(f);
    const t = TH.name;
    // hero still
    const bm = D.hero ? IMG.get(D.hero.url) : null;
    const lines = nameLines(D.model.name, L - 2 * M, 150);
    let size = Math.min(150, ...lines.map(l => fitSize(l, 150, L - 2 * M, 700, null, -0.02)));
    if (lines.length > 1) size = Math.min(size, 112);
    const y0 = lines.length > 1 ? 146 : 184;
    const nameBottom = y0 + (lines.length - 1) * size * 0.98 + size * 0.2;
    if (bm) {
      const r = heroRect(nameBottom + 26);
      const hp = ramp(f, m.hero, m.hero + b * 1.5);
      const push = 1 + 0.045 * ramp(f, s.start, s.end);
      const cx = (r.box[0] + r.box[2]) / 2, cy = (r.box[1] + r.box[3]) / 2;
      CX.save();
      // ground: shadow / platform under the model
      const gy = r.box[3] - 6, gw = (r.box[2] - r.box[0]) * 0.52;
      if (t === 'scan') {
        CX.strokeStyle = rgba(TH.accent, 0.5 * hp); CX.lineWidth = 2;
        for (let k = 0; k < 3; k++) { CX.beginPath(); CX.ellipse(cx, gy, gw * (1 + k * 0.22) * E.outCubic(hp), 22 * (1 + k * 0.22), 0, 0, Math.PI * 2); CX.stroke(); }
      } else if (t === 'tape') {
        const g = CX.createRadialGradient(cx, gy, 10, cx, gy, gw * 1.3);
        g.addColorStop(0, rgba(TH.accent, 0.45 * hp)); g.addColorStop(1, rgba(TH.accent, 0));
        CX.fillStyle = g; CX.beginPath(); CX.ellipse(cx, gy, gw * 1.3, 60, 0, 0, Math.PI * 2); CX.fill();
      } else {
        CX.fillStyle = rgba('#000000', 0.16 * hp); CX.filter = `blur(${16 * S}px)`;
        CX.beginPath(); CX.ellipse(cx, gy, gw, 26, 0, 0, Math.PI * 2); CX.fill(); CX.filter = 'none';
      }
      CX.translate(cx, cy); CX.scale(push, push); CX.translate(-cx, -cy);
      if (!D.hero.cutout) {                       // an opaque still: a framed card
        CX.beginPath(); CX.roundRect(r.box[0], r.box[1], r.box[2] - r.box[0], r.box[3] - r.box[1], 28); CX.clip();
      }
      if (t === 'scan') {                         // scanned in from the bottom, glowing edge
        const ly = lerp(r.box[3] + 20, r.box[1] - 20, E.inOutCubic(hp));
        CX.save(); CX.beginPath(); CX.rect(0, ly, L, L); CX.clip();
        CX.drawImage(bm, r.x, r.y, r.w, r.h); CX.restore();
        if (hp < 1) {
          const g = CX.createLinearGradient(0, ly - 30, 0, ly + 30);
          g.addColorStop(0, rgba(TH.accent, 0)); g.addColorStop(0.5, rgba(TH.accent, 0.7)); g.addColorStop(1, rgba(TH.accent, 0));
          CX.fillStyle = g; CX.fillRect(r.box[0] - 60, ly - 30, r.box[2] - r.box[0] + 120, 60);
        }
      } else if (t === 'tape') {                  // slices slide in, glitchy
        const n = 24, hh = r.h / n;
        for (let i = 0; i < n; i++) {
          const d = (1 - E.outExpo(clamp(hp * 1.4 - hash(i, 5) * 0.4))) * (hash(i, 6) - 0.5) * 900;
          const a = clamp(hp * 3 - hash(i, 9));
          if (a <= 0) continue;
          CX.globalAlpha = a;
          CX.drawImage(bm, 0, i * bm.height / n, bm.width, bm.height / n, r.x + d, r.y + i * hh, r.w, hh + 0.5);
        }
        CX.globalAlpha = 1;
      } else if (t === 'playful') {               // pops up with a squash
        const q = E.spring(hp, 1.6, 5.5);
        const sy = 0.6 + 0.4 * q, sx = 1.25 - 0.25 * q;
        CX.translate(cx, r.box[3]); CX.scale(sx * q, sy * q); CX.translate(-cx, -r.box[3]);
        CX.drawImage(bm, r.x, r.y, r.w, r.h);
      } else {                                    // an iris opens
        CX.beginPath(); CX.arc(cx, cy, 760 * E.outCubic(hp), 0, Math.PI * 2); CX.clip();
        const sc = 1.1 - 0.1 * E.outCubic(hp);
        CX.translate(cx, cy); CX.scale(sc, sc); CX.translate(-cx, -cy);
        CX.drawImage(bm, r.x, r.y, r.w, r.h);
      }
      CX.restore();
    }
    // the name
    const fnt = font(size, 700);
    let idx = 0;
    lines.forEach((ln, li) => {
      const y = y0 + li * size * 0.98;
      const base = idx;
      const col = t === 'playful' ? TH.ink : TH.ink;
      if (t === 'decode') { /* unreachable: styles keyed by theme.title below */ }
      const style = TH.title;
      if (style === 'decode') {
        const glyph = '#%&@0123456789<>/\\{}[]=+*ABCDEFGHKMNRSTXZ';
        kinetic(ln, L / 2, y, fnt, (i, n, gl) => {
          const t0 = m.name + (base + i) * 1.6;
          const lock = t0 + 9;
          if (f < t0) return { alpha: 0 };
          if (f < lock) {
            const ch = glyph[Math.floor(hash(f, base + i) * glyph.length)];
            return { ch, color: TH.accent, alpha: 0.85 };
          }
          const fl = clamp(1 - (f - lock) / 6);
          return { color: fl > 0 ? mix(TH.ink, '#ffffff', fl) : TH.ink };
        }, { align: 'center', spacing: -size * 0.02 });
        if (f >= m.name) {
          const w = measure(ln, fnt, -size * 0.02);
          const q = tw(f, m.name, m.name + b, E.outExpo);
          brackets(L / 2 - w / 2 - 24, y - size * 0.8, L / 2 + w / 2 + 24, y + size * 0.14, 22, rgba(TH.hud, q), 3);
        }
      } else if (style === 'osd') {
        kinetic(ln, L / 2, y, fnt, (i) => {
          const t0 = m.name + (base + i) * 1.2;
          if (f < t0) return { alpha: 0 };
          const q = clamp((f - t0) / 4);
          const jit = (1 - q) * (hash(f, i) - 0.5) * 30;
          return { dx: jit, alpha: q > 0 ? 1 : 0 };
        }, { align: 'center', spacing: -size * 0.02 });
        // chroma ghosts
        CX.save(); CX.globalCompositeOperation = 'screen';
        const q = tw(f, m.name, m.name + b * 2);
        text(ln, L / 2 - 6 * (1 - q) - 3, y, { font: fnt, color: TH.accent, alpha: 0.55, align: 'center', spacing: -size * 0.02 });
        text(ln, L / 2 + 6 * (1 - q) + 3, y, { font: fnt, color: TH.accent2, alpha: 0.55, align: 'center', spacing: -size * 0.02 });
        CX.restore();
        text(ln, L / 2, y, { font: fnt, color: TH.ink, align: 'center', spacing: -size * 0.02,
          alpha: clamp((f - m.name - (base + ln.length) * 1.2) / 3) });
      } else if (style === 'bounce') {
        kinetic(ln, L / 2, y, fnt, (i, n) => {
          const t0 = m.name + (base + i) * 1.8;
          const k = f - t0;
          if (k < 0) return { alpha: 0 };
          const fall = 7;
          if (k < fall) {
            const q = k / fall;
            return { dy: -420 * (1 - q * q), sx: 0.82, sy: 1.25 };
          }
          const j = k - fall;
          const w = Math.exp(-j / 4) * Math.cos(j * 0.9);
          const cols = [TH.accent, TH.accent2, '#2BB673', '#3D7DFF'];
          return { sx: 1 + 0.28 * w, sy: 1 - 0.28 * w, dy: -w * 18 + size * 0.14 * w, color: j < 6 ? cols[(base + i) % cols.length] : TH.ink };
        }, { align: 'center', spacing: -size * 0.01 });
      } else {                                    // slam: masked rise with overshoot
        CX.save(); CX.beginPath(); CX.rect(0, y - size * 1.05, L, size * 1.3); CX.clip();
        kinetic(ln, L / 2, y, fnt, (i) => {
          const t0 = m.name + (base + i) * 1.4;
          const q = clamp((f - t0) / 9);
          if (q <= 0) return { alpha: 0 };
          return { dy: (1 - E.outBack(q, 1.9)) * size * 1.1 };
        }, { align: 'center', spacing: -size * 0.02 });
        CX.restore();
      }
      idx += ln.length;
    });
    // piece counter
    const cp = ramp(f, m.count0, m.count1);
    const pop = f >= m.count1 ? 1 + 0.08 * Math.exp(-(f - m.count1) / 3) * Math.cos((f - m.count1) * 0.9) : 1;
    const csize = 104;
    const ca = tw(f, m.count0 - 4, m.count0 + 2);
    if (ca > 0) {
      CX.save(); CX.globalAlpha = ca;
      label('pieces', M + 4, 876, { color: TH.name === 'brand' || TH.name === 'playful' ? TH.ink : TH.hud });
      CX.translate(M, 1000); CX.scale(pop, pop); CX.translate(-M, -1000);
      const n = Math.round(D.model.pieces * 1);
      odometer(n, M, 1000, csize, cp, { color: TH.name === 'tape' ? TH.ink : TH.ink });
      CX.restore();
    }
    // stat chips to the right of the counter, at most two rows (smaller chips if need be)
    const cw = measure(fmt(D.model.pieces), font(csize, 700)) + M + 40;
    const x0c = Math.max(cw, 360);
    // one compact row: keep the chips that fit at a readable size
    const widths = D.chips.map((c, k) => chip(UP(c.value), c.label, 0, -999, 0, k));   // measure
    let n = widths.length, sc = 1;
    const rowW = (k, s_) => widths.slice(0, k).reduce((a, w) => a + w * s_ + 14 * s_, -14 * s_);
    for (;;) {
      sc = Math.min(1, (L - M - x0c) / rowW(n, 1));
      if (sc >= 0.86 || n <= 3) break;
      n--;
    }
    const place = [];
    let xx = x0c;
    widths.slice(0, n).forEach(w => { place.push([xx, 0]); xx += (w + 14) * sc; });
    D.chips.slice(0, n).forEach((c, k) => {
      const t0 = m.chips[k] !== undefined ? m.chips[k] : m.chips[m.chips.length - 1] + (k - m.chips.length + 1) * 4;
      const [x, row] = place[k];
      const y = 930 + row * 74 * sc;
      CX.save(); CX.translate(x, y); CX.scale(sc, sc);
      chip(UP(c.value), c.label, 0, 0, ramp(f, t0, t0 + 9), k);
      CX.restore();
    });
  },
};

// ------------------------------------------------------------------------------ build
function landedAt(f) {                // parts landed by frame f (binary search)
  const a = D.build.land;
  let lo = 0, hi = a.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (a[mid] <= f) lo = mid + 1; else hi = mid; }
  return lo;
}
function sectionAt(f) {
  const S_ = D.build.sections;
  let k = 0;
  for (let i = 0; i < S_.length; i++) if (f >= S_[i].start) k = i;
  return k;
}

SEG.build = {
  async prepare(f) { return plate('build', f); },
  shake(f) { shakeAt(f, [D.build.land_last], 7, 8); },
  draw(f, s, bm) {
    drawPlate(bm);
    const b = B();
    const n = landedAt(f), total = D.build.land.length;
    const step = n ? D.build.step[n - 1] : 0;
    const pieces = Math.round(D.model.pieces * n / total);
    const done = f >= D.build.land_last;
    const k = sectionAt(f);
    const sec = D.build.sections[k];
    const t = TH.name;
    // landing rings on the first parts
    for (const [lf, x, y] of D.build.pulses) {
      const q = (f - lf) / 14;
      if (q < 0 || q > 1) continue;
      CX.save(); CX.strokeStyle = rgba(t === 'brand' ? TH.accent : TH.xray, 1 - q); CX.lineWidth = 3 * (1 - q) + 0.5;
      circle(x, y, 8 + 46 * E.outCubic(q)); CX.stroke(); CX.restore();
    }
    // the final piece
    const fin = D.build.final;
    const fk = f - fin.start;
    if (fk >= 0 && fin.track.length) {
      const [x, y] = fin.track[Math.min(fk, fin.track.length - 1)];
      const q = clamp(fk / 16);
      CX.save();
      CX.strokeStyle = rgba(TH.name === 'brand' || TH.name === 'playful' ? TH.accent : TH.xray, 1 - q); CX.lineWidth = 6 * (1 - q) + 1;
      circle(x, y, 20 + 140 * E.outCubic(q)); CX.stroke();
      CX.restore();
      const lp = tw(f, fin.start + 2, fin.start + 12, E.outExpo);
      const lx = x < L / 2 ? Math.min(L - M - 300, x + 150) : Math.max(M, x - 450);
      const ly = Math.max(M + 190, y - 150);
      CX.save(); CX.globalAlpha = lp;
      CX.strokeStyle = t === 'brand' || t === 'playful' ? TH.ink : TH.hud; CX.lineWidth = 2.5;
      CX.beginPath(); CX.moveTo(x, y); CX.lineTo(lerp(x, lx + (x < L / 2 ? 0 : 300), lp), lerp(y, ly + 14, lp)); CX.stroke();
      circle(x, y, 6); CX.fillStyle = CX.strokeStyle; CX.fill();
      CX.restore();
      calloutLabel('Final piece', `${fmt(D.model.pieces)} of ${fmt(D.model.pieces)}`, x < L / 2 ? lx : lx + 300, ly, x < L / 2 ? 'left' : 'right', lp, 0);
    }
    // HUD: section lower third
    const ls = sec.start + (k === 0 ? b : 3), le = Math.min(sec.start + b * 5, (D.build.sections[k + 1] || { start: s.end }).start - 4, done ? D.build.land_last : 1e9);
    const lp = tw(f, ls, ls + 10, E.outExpo) * (1 - tw(f, le - 8, le, E.inCubic));
    if (lp > 0 && sec.title) lowerThird(k + 1, sec.title, lp, f - ls);
    // HUD: step and pieces
    const st = UP(t === 'playful' ? 'step' : 'step');
    const nSteps = D.model.steps;
    if (D.build.ground_up) {
      const hgt = n ? D.build.height[n - 1] : 0;
      heightCounter(f, s, hgt, D.build.height[D.build.height.length - 1]);
    } else {
      hudCounters(f, s, step, nSteps, pieces, done);
    }
    // progress bar with section ticks
    progressBar(f, s, n / total, done);
    const fast = rateAt(f) > 4;
    osd(f, s, done ? '❚❚ PAUSE' : fast ? '▶▶ FF' : '▶ PLAY');
    visor(f, s, `BUILD · SEC ${String(k + 1).padStart(2, '0')}`);
  },
};
function rateAt(f) {                  // parts landing per frame around f
  return (landedAt(f + 8) - landedAt(f - 8)) / 16;
}

function lowerThird(num, title, p, k) {
  const t = TH.name;
  const x = M, y = TOPY() + 8;
  const tsize = Math.min(56, fitSize(UP(title), 56, 620, 700));
  const tw_ = measure(UP(title), font(tsize, 700), -1);
  CX.save();
  const slide = (1 - p) * -60;
  CX.translate(slide, 0); CX.globalAlpha = clamp(p * 1.5);
  if (t === 'scan') {
    label(`section ${String(num).padStart(2, '0')}`, x, y - 20, { color: TH.hud });
    CX.fillStyle = rgba(TH.bg, 0.55); CX.fillRect(x - 12, y - 4, tw_ + 36, tsize + 18);
    brackets(x - 12, y - 4, x + tw_ + 24, y + tsize + 14, 12, TH.hud, 2);
    text(UP(title), x + 6, y + tsize * 0.86, { size: tsize, color: TH.ink, spacing: -1 });
  } else if (t === 'tape') {
    text(`CHAPTER ${String(num).padStart(2, '0')}`, x, y + 6, { font: font(40, 400, 'VT323'), color: TH.accent2, shadow: rgba('#000', 0.8), sx: 3, sy: 3, spacing: 2 });
    text(UP(title), x, y + 12 + tsize * 0.95, { size: tsize, color: TH.ink, shadow: rgba(TH.accent, 0.8), sx: 4, sy: 0, spacing: -1 });
  } else if (t === 'playful') {
    const bw = tw_ + 130, bh = tsize + 34;
    const sq = E.spring(clamp(k / 16), 1.6, 5);
    CX.translate(x + 40, y + bh / 2); CX.scale(lerp(1.3, 1, sq), lerp(0.7, 1, sq)); CX.translate(-x - 40, -y - bh / 2);
    CX.fillStyle = rgba('#000', 0.14); rrect(x + 5, y + 7, bw, bh, bh / 2); CX.fill();
    CX.fillStyle = TH.bg2; rrect(x, y, bw, bh, bh / 2); CX.fill();
    CX.fillStyle = TH.accent; circle(x + bh / 2, y + bh / 2, bh / 2 - 8); CX.fill();
    text(String(num), x + bh / 2, y + bh / 2 + 13, { size: 38, color: '#fff', align: 'center' });
    text(UP(title), x + bh + 10, y + bh / 2 + tsize * 0.36, { size: tsize, color: TH.ink, spacing: -1 });
  } else {
    const bh = tsize + 30;
    CX.fillStyle = TH.accent; rrect(x, y, bh, bh, 14); CX.fill();
    text(String(num).padStart(2, '0'), x + bh / 2, y + bh / 2 + 15, { size: 42, color: '#fff', align: 'center' });
    const w2 = tw_ + 48;
    CX.fillStyle = TH.ink; rrect(x + bh + 8, y, w2 * clamp(p * 1.3), bh, 14); CX.fill();
    CX.save(); CX.beginPath(); CX.rect(x + bh + 8, y, w2 * clamp(p * 1.3), bh); CX.clip();
    text(UP(title), x + bh + 32, y + bh / 2 + tsize * 0.36, { size: tsize, color: TH.bg, spacing: -1 });
    CX.restore();
  }
  CX.restore();
}

function hudCounters(f, s, step, nSteps, pieces, done) {
  const t = TH.name;
  const x = L - M; let y = 118;
  if (t === 'tape') {
    y = TOPY() - 60;
    const o = { font: font(40, 400, 'VT323'), color: TH.ink, shadow: rgba('#000', 0.8), sx: 3, sy: 3, align: 'right', spacing: 2 };
    text(`STEP ${String(step).padStart(3, '0')}/${nSteps}`, x, y + 36, o);
    return;
  }
  const lc = t === 'scan' ? TH.hud : t === 'brand' || t === 'playful' ? TH.ink : TH.ink;
  label('step', x, y - 2, { align: 'right', color: lc });
  const str = `${String(step).padStart(String(nSteps).length, '0')}`;
  const fnt = font(64, 700);
  const w2 = measure(` / ${nSteps}`, font(34, 600));
  text(str, x - w2, y + 60, { font: fnt, color: t === 'scan' ? TH.ink : TH.ink, align: 'right',
    shadow: t === 'scan' ? null : rgba('#ffffff', 0.6), blur: 12 });
  text(` / ${nSteps}`, x, y + 60, { font: font(34, 600), color: lc, align: 'right', alpha: 0.8 });
}

// how high the build has grown (mm above the table)
function heightCounter(f, s, mm, total) {
  const t = TH.name;
  const x = L - M;
  const unit = total >= 250 ? 'cm' : 'mm';
  const v = unit === 'cm' ? (mm / 10).toFixed(1) : String(Math.round(mm));
  const tot = unit === 'cm' ? (total / 10).toFixed(1) : String(Math.round(total));
  if (t === 'tape') {
    const o = { font: font(40, 400, 'VT323'), color: TH.ink, shadow: rgba('#000', 0.8), sx: 3, sy: 3, align: 'right', spacing: 2 };
    text(`HEIGHT ${v}/${tot} ${UP(unit)}`, x, TOPY() - 24, o);
    return;
  }
  const y = 118;
  const lc = t === 'scan' ? TH.hud : TH.ink;
  label('height', x, y - 2, { align: 'right', color: lc });
  const w2 = measure(` / ${tot} ${unit}`, font(34, 600));
  text(v, x - w2, y + 60, { font: font(64, 700), color: TH.ink, align: 'right',
    shadow: t === 'scan' ? null : rgba('#ffffff', 0.6), blur: 12 });
  text(` / ${tot} ${unit}`, x, y + 60, { font: font(34, 600), color: lc, align: 'right', alpha: 0.8 });
}

function progressBar(f, s, p, done) {
  const t = TH.name;
  const x0 = M, x1 = L - M, y = L - M - 8;
  const secs = D.build.sections;
  const tot = D.build.land.length;
  const pieces = Math.round(D.model.pieces * p);
  const flash = done ? Math.exp(-(f - D.build.land_last) / 5) : 0;
  CX.save();
  if (t === 'tape') {
    // a VCR counter strip, stopping short of the timecode
    const xe = x1 - 190;
    CX.fillStyle = rgba('#000', 0.5); CX.fillRect(x0, y - 8, xe - x0, 16);
    CX.fillStyle = TH.accent; CX.fillRect(x0, y - 8, (xe - x0) * p, 16);
    text(`${fmt(pieces)} / ${fmt(D.model.pieces)} PCS`, x0, y - 22, { font: font(40, 400, 'VT323'), color: TH.ink, shadow: rgba('#000', 0.8), sx: 3, sy: 3, spacing: 2 });
    CX.restore();
    return;
  }
  const trackCol = t === 'scan' ? rgba(TH.hud, 0.25) : rgba(TH.ink, 0.16);
  const fillCol = t === 'scan' ? TH.hud : TH.accent;
  const h = t === 'scan' ? 4 : 14;
  if (t !== 'scan') { CX.fillStyle = rgba('#ffffff', 0.7); rrect(x0 - 4, y - h / 2 - 4, x1 - x0 + 8, h + 8, (h + 8) / 2); CX.fill(); }
  CX.fillStyle = trackCol; rrect(x0, y - h / 2, x1 - x0, h, h / 2); CX.fill();
  CX.fillStyle = flash > 0.02 ? mix(fillCol, '#ffffff', flash) : fillCol;
  rrect(x0, y - h / 2, Math.max(h, (x1 - x0) * p), h, h / 2); CX.fill();
  if (t === 'scan') {
    CX.shadowColor = TH.hud; CX.shadowBlur = 12;
    CX.fillRect(x0 + (x1 - x0) * p - 2, y - 9, 4, 18);
    CX.shadowBlur = 0;
  }
  // section ticks: where each section starts in pieces
  let acc = 0;
  CX.fillStyle = t === 'scan' ? TH.hud : TH.ink;
  secs.forEach((sc, i) => {
    if (i > 0) { const xx = x0 + (x1 - x0) * acc / tot; CX.fillRect(xx - 1, y - h / 2 - 7, 2, h + 14); }
    acc += sc.parts;
  });
  const lc = t === 'scan' ? TH.hud : TH.ink;
  const txt = `${fmt(pieces)} / ${fmt(D.model.pieces)}`;
  text(txt, x1, y - 24, { size: 34, color: t === 'scan' ? TH.ink : TH.ink, align: 'right',
    shadow: t === 'scan' ? null : rgba('#ffffff', 0.7), blur: 10 });
  label('pieces', x1 - measure(txt, font(34, 700)) - 14, y - 26, { align: 'right', color: lc });
  if (done) {
    const q = tw(f, D.build.land_last, D.build.land_last + 10);
    CX.save(); CX.translate(x0 + 30, y - 38);
    statusIcon(0, 0, 22, 'pass', q);
    CX.restore();
    label('complete', x0 + 64, y - 30, { color: lc, alpha: q });
  }
  CX.restore();
}

// ------------------------------------------------------------------------------ scan
SEG.scan = {
  async prepare(f) { return plate('scan', f); },
  draw(f, s, bm) {
    drawPlate(bm);
    const m = D.marks.scan, b = B();
    const box = D.shots.scan.box;
    const lay = D.shots.scan.layout;
    const sp = E.inOutCubic(ramp(f, m.sweep0, m.sweep1));
    const y0 = box[3] + 30, y1 = box[1] - 30;
    const ly = lerp(y0, y1, sp);
    const xr = (f >= m.sweep0 ? 1 : 0) * (1 - tw(f, m.fade0, m.fade1, E.inOutCubic));
    if (xr > 0) {
      CX.save();
      CX.beginPath(); CX.rect(0, ly, L, L - ly); CX.clip();
      CX.globalAlpha = 0.84 * xr; CX.fillStyle = TH.xray_bg; CX.fillRect(0, 0, L, L);
      CX.restore();
      drawWire(f, { clip: c => { c.beginPath(); c.rect(0, ly, L, L - ly); c.clip(); }, alpha: 0.5 * xr, width: 1.1 });
      // connection points: they flash as the line passes them
      const pts = (D.scan && D.scan.points) || [];
      const cam = camAt(f);
      CX.save(); CX.globalCompositeOperation = 'lighter';
      for (const [x, y, z] of pts) {
        const P = proj(cam, x, y, z);
        if (P[1] < ly) continue;
        const since = (P[1] - ly);
        const flash = Math.exp(-since / 40);
        CX.fillStyle = rgba(TH.name === 'brand' ? '#FFD84A' : TH.accent2, (0.35 + 0.65 * flash) * xr);
        circle(P[0], P[1], 1.8 + 2.6 * flash); CX.fill();
      }
      CX.restore();
    }
    // the scan line
    const la = tw(f, m.sweep0 - 4, m.sweep0 + 2) * (1 - tw(f, m.sweep1, m.sweep1 + 6));
    if (la > 0) {
      const x0 = box[0] - 70, x1 = box[2] + 70;
      CX.save(); CX.globalAlpha = la;
      const g = CX.createLinearGradient(0, ly - 60, 0, ly + 10);
      g.addColorStop(0, rgba(TH.xray, 0)); g.addColorStop(0.85, rgba(TH.xray, 0.35)); g.addColorStop(1, rgba(TH.xray, 0));
      CX.fillStyle = g; CX.fillRect(x0, ly - 60, x1 - x0, 70);
      CX.shadowColor = TH.xray; CX.shadowBlur = 18;
      CX.fillStyle = mix(TH.xray, '#ffffff', 0.6); CX.fillRect(x0, ly - 1.5, x1 - x0, 3);
      CX.shadowBlur = 0;
      CX.fillStyle = TH.xray;
      for (let x = x0; x <= x1; x += 24) CX.fillRect(x, ly - 7, 1.5, 14);
      label(`scan ${String(Math.round(sp * 100)).padStart(3, ' ')}%`, x1 + 10, ly + 6, { color: TH.xray, size: TH.mono === 'VT323' ? 30 : 18 });
      CX.restore();
    }
    checksPanel(f, s, lay);
    osd(f, s, '❚❚ PAUSE');
    visor(f, s, 'STRUCTURAL SCAN');
  },
};

function checksPanel(f, s, lay) {
  const m = D.marks.scan, b = B();
  const rows = D.checks.rows;
  const t = TH.name;
  const side = lay === 'side';
  const cols = side ? 1 : 2;
  const perCol = Math.ceil(rows.length / cols);
  const rh = side ? 82 : 86;
  const ph = 96 + perCol * rh;
  const bottom = L - M - (t === 'tape' ? 44 : 0);
  const px = side ? 596 : M - 8, py = side ? Math.min(176, bottom - ph) : bottom - ph;
  const pw = side ? L - M - px + 12 : L - 2 * M + 16;
  const pa = tw(f, s.start + 2, s.start + 12, E.outExpo);
  CX.save();
  CX.translate((1 - pa) * 40, 0);
  panel(px, py, pw, ph, { alpha: pa });
  CX.globalAlpha = pa;
  label('checked by computer', px + 26, py + 42, { color: t === 'scan' ? TH.hud : t === 'tape' ? TH.accent2 : TH.accent, size: TH.mono === 'VT323' ? 32 : 20 });
  text(UP(D.model.name), px + 26, py + 76, { size: 26, color: TH.panel_ink, alpha: 0.75 });
  CX.restore();
  const colW = (pw - 32) / cols;
  rows.forEach((r, i) => {
    const t0 = m.checks[i];
    const q = ramp(f, t0, t0 + 10);
    if (q <= 0) return;
    const c = Math.floor(i / perCol), k = i % perCol;
    const x = px + 22 + c * colW, y = py + 104 + k * rh;
    CX.save();
    CX.globalAlpha = clamp(q * 3); CX.translate((1 - E.outExpo(q)) * 40, 0);
    statusIcon(x + 22, y + rh / 2 - 8, 20, r.status, q, r.na);
    const tx = x + 58;
    text(r.title, tx, y + rh / 2 - 14, { size: 27, color: TH.panel_ink, weight: 600 });
    // the detail line, cut to the room left of the headline number
    const sfont = monoFont(TH.mono === 'VT323' ? 26 : 17);
    const room = colW - 58 - measure(r.big, font(38, 700)) - 44;
    let small = r.small;
    if (measure(small, sfont, 0.4) > room) {
      const parts = small.split(' \u00b7 ');
      while (parts.length > 1 && measure(parts.join(' \u00b7 '), sfont, 0.4) > room) parts.pop();
      small = parts.join(' \u00b7 ');
      while (small.length > 4 && measure(small + '\u2026', sfont, 0.4) > room) small = small.slice(0, -1);
      if (small !== parts.join(' \u00b7 ') || measure(small, sfont, 0.4) > room) small += '\u2026';
    }
    text(small, tx, y + rh / 2 + 15, { font: sfont, color: t === 'scan' ? rgba(TH.ink, 0.62) : TH.muted, spacing: 0.4 });
    // the headline number counts up
    let big = r.big;
    const num = parseFloat(String(big).replace(/[^0-9.]/g, ''));
    if (!isNaN(num) && /^[0-9,]+(°)?$/.test(big)) {
      const v = num * E.outCubic(clamp(q * 1.2));
      big = fmt(v) + (big.endsWith('°') ? '°' : '');
    }
    const col = r.status === 'warn' ? TH.warn : r.status === 'fail' ? TH.accent : (t === 'scan' || t === 'tape' ? TH.ink : TH.ink);
    text(big, x + colW - 26, y + rh / 2 + 2, { size: 38, color: r.na ? TH.muted : col, align: 'right' });
    CX.restore();
  });
  // summary stamp
  const sq = ramp(f, m.summary, m.summary + 12);
  if (sq > 0) {
    const allPass = D.checks.rows.every(r => r.status === 'pass');
    const str = UP(D.checks.summary);
    const col = D.checks.rows.some(r => r.status === 'fail') ? TH.accent : allPass ? TH.ok : TH.warn;
    const fnt = font(34, 700);
    const w = measure(str, fnt) + 56;
    // at the header's right if there's room, else under the panel
    const head = Math.max(measure(UP(D.model.name), font(26, 700)), 260) + 40;
    const below = pw - head < w + 20;
    const sx = below ? px + (pw - w) / 2 : px + pw - w - 20, sy = below ? py + ph + 18 : py + 22;
    CX.save();
    const sc = t === 'playful' ? E.spring(sq, 1.8, 6) : 1 + 0.6 * (1 - E.outBack(sq, 2));
    CX.translate(sx + w / 2, sy + 30); CX.scale(sc, sc); CX.rotate(t === 'brand' || t === 'playful' ? -0.05 : 0);
    CX.globalAlpha = clamp(sq * 3);
    if (t === 'scan' || t === 'tape') {
      CX.fillStyle = rgba(col, 0.16); CX.fillRect(-w / 2, -30, w, 60);
      CX.strokeStyle = col; CX.lineWidth = 2.5; CX.strokeRect(-w / 2, -30, w, 60);
    } else {
      CX.strokeStyle = col; CX.lineWidth = 5; rrect(-w / 2, -30, w, 60, 12); CX.stroke();
    }
    text(str, 0, 12, { font: fnt, color: col, align: 'center' });
    CX.restore();
  }
}

// ------------------------------------------------------------------------------ mechanism
function calloutLabel(title, sub, x, y, side, p, k) {
  if (p <= 0) return;
  const t = TH.name;
  const al = side === 'left' ? 'left' : 'right';
  const ts = 34, ss = TH.mono === 'VT323' ? 30 : 20;
  const tw_ = measure(UP(title), font(ts, 700), -0.5);
  const sw = measure(TH.mono === 'Fredoka' ? sub : UP(sub), monoFont(ss), ss * 0.1);
  const w = Math.max(tw_, sw) + 40, h = sub ? 86 : 58;
  const bx = side === 'left' ? x : side === 'center' ? x - w / 2 : x - w;
  CX.save();
  CX.globalAlpha = clamp(p * 2.5);
  const reveal = E.outExpo(p);
  const cx0 = side === 'left' ? bx : side === 'center' ? bx + w * (1 - reveal) / 2 : bx + w * (1 - reveal);
  CX.beginPath(); CX.rect(cx0 - 6, y - 12, w * reveal + 12, h + 24); CX.clip();
  if (t === 'scan') {
    CX.fillStyle = rgba(TH.bg, 0.66); CX.fillRect(bx, y, w, h);
    brackets(bx - 3, y - 3, bx + w + 3, y + h + 3, 12, TH.hud, 2);
  } else if (t === 'tape') {
    CX.fillStyle = rgba('#000', 0.55); CX.fillRect(bx, y, w, h);
    CX.fillStyle = k % 2 ? TH.accent2 : TH.accent; CX.fillRect(side === 'left' ? bx : bx + w - 5, y, 5, h);
  } else if (t === 'playful') {
    const cols = [TH.accent, TH.accent2, '#2BB673', '#3D7DFF'];
    CX.fillStyle = rgba('#000', 0.14); rrect(bx + 4, y + 6, w, h, 20); CX.fill();
    CX.fillStyle = cols[k % cols.length]; rrect(bx, y, w, h, 20); CX.fill();
  } else {
    CX.fillStyle = TH.ink; rrect(bx, y, w, h, 14); CX.fill();
  }
  const fg = t === 'playful' ? onColour([TH.accent, TH.accent2, '#2BB673', '#3D7DFF'][k % 4]) : t === 'brand' ? TH.bg : TH.ink;
  const sc = t === 'brand' ? TH.bg2 : t === 'scan' ? TH.hud : t === 'tape' ? (k % 2 ? TH.accent2 : TH.accent) : fg;
  const tx = side === 'left' ? bx + 20 : side === 'center' ? bx + w / 2 : bx + w - 20;
  const al2 = side === 'center' ? 'center' : al;
  text(UP(title), tx, y + 44, { size: ts, color: fg, align: al2, spacing: -0.5 });
  if (sub) text(TH.mono === 'Fredoka' ? sub : UP(sub), tx, y + 72, { font: monoFont(ss), color: sc, align: al2, spacing: ss * 0.1, alpha: 0.95 });
  CX.restore();
}

SEG.mechanism = {
  async prepare(f) { return plate('mechanism', f); },
  draw(f, s, bm) {
    drawPlate(bm);
    const MM = D.mechanism, m = D.marks.mechanism, b = B();
    const k = f - s.start;
    const G = MM.groups[Math.min(k, MM.groups.length - 1)] || null;
    // x-ray outlines of the parts hidden inside
    const xs = new Set();
    MM.callouts.forEach((c, j) => { if (c.xray && f >= m.callouts[j]) c.parts.forEach(p => xs.add(p)); });
    if (xs.size) {
      const a = tw(f, m.callouts[0], m.callouts[0] + b);
      drawWire(f, { parts: xs, groups: G, alpha: 0.9 * a, width: 3.2, color: rgba(TH.xray, 0.35) });
      drawWire(f, { parts: xs, groups: G, alpha: 0.95 * a, width: 1.3 });
    }
    // callouts
    const lineCol = TH.name === 'brand' || TH.name === 'playful' ? TH.ink : TH.hud;
    MM.callouts.forEach((c, j) => {
      const t0 = m.callouts[j];
      const p = ramp(f, t0, t0 + 12);
      if (p <= 0) return;
      const [tx, ty] = c.attach;
      CX.save();
      CX.strokeStyle = lineCol; CX.lineWidth = 2.2;
      CX.shadowColor = TH.name === 'brand' || TH.name === 'playful' ? 'rgba(255,255,255,0.8)' : rgba(TH.hud, 0.6);
      CX.shadowBlur = 6;
      c.anchors.forEach(a => {
        const [ax, ay] = a.track[Math.min(k, a.track.length - 1)];
        const q = E.outCubic(clamp(p * 1.4));
        // anchor -> (elbow) -> label, drawn on
        const pts = [[ax, ay], ...(c.elbow ? [c.elbow] : []), [tx, ty]];
        const lens = pts.slice(1).map((pt, i) => Math.hypot(pt[0] - pts[i][0], pt[1] - pts[i][1]));
        let d = q * lens.reduce((x, y) => x + y, 0);
        CX.beginPath(); CX.moveTo(ax, ay);
        for (let i = 1; i < pts.length; i++) {
          const l = lens[i - 1];
          if (d >= l) { CX.lineTo(pts[i][0], pts[i][1]); d -= l; }
          else { const r = l > 0 ? d / l : 1; CX.lineTo(lerp(pts[i - 1][0], pts[i][0], r), lerp(pts[i - 1][1], pts[i][1], r)); break; }
        }
        CX.stroke();
        // anchor dot and ring
        CX.fillStyle = TH.name === 'brand' ? TH.accent : TH.name === 'playful' ? TH.accent : TH.hud;
        circle(ax, ay, 6.5 * E.outBack(clamp(p * 2))); CX.fill();
        const rp = ((f - t0) % 24) / 24;
        CX.strokeStyle = rgba(TH.name === 'brand' || TH.name === 'playful' ? TH.accent : TH.hud, 1 - rp);
        CX.lineWidth = 2; circle(ax, ay, 8 + 18 * rp); CX.stroke();
        CX.strokeStyle = lineCol; CX.lineWidth = 2.2;
      });
      CX.restore();
      const title = c.n > 1 ? `${c.label} \u00d7 ${c.n}` : c.label;
      calloutLabel(title, c.sub, c.lx, c.ly, c.align, ramp(f, t0 + 6, t0 + 18), j);
    });
    // header (until the callouts arrive; the gauge keeps the name) and the pose gauge
    const c0 = m.callouts.length ? m.callouts[0] : s.end;
    const ha = tw(f, s.start + 2, s.start + 12, E.outExpo) * (1 - tw(f, c0 - 6, c0 + 2, E.inCubic));
    CX.save(); CX.globalAlpha = ha;
    label('mechanism', M, TOPY(), { color: TH.name === 'scan' ? TH.hud : TH.name === 'tape' ? TH.accent2 : TH.accent });
    text(UP(MM.name), M, TOPY() + 52, { size: fitSize(UP(MM.name), 52, 620, 700), color: TH.name === 'brand' || TH.name === 'playful' ? TH.ink : TH.ink,
      shadow: TH.name === 'brand' || TH.name === 'playful' ? rgba('#ffffff', 0.7) : rgba('#000', 0.5), blur: 12 });
    CX.restore();
    gauge(f, s);
    osd(f, s, '▶ SLOW');
    visor(f, s, 'MECHANISM TRACK');
  },
};

function gauge(f, s) {
  const MM = D.mechanism, m = D.marks.mechanism;
  const k = Math.min(f - s.start, MM.u.length - 1);
  const u = MM.u[k];
  const p = tw(f, m.gauge, m.gauge + 12, E.outExpo);
  if (p <= 0) return;
  const t = TH.name;
  const w = 480, x0 = L / 2 - w / 2, y = L - M - (TH.name === 'tape' ? 84 : 40);
  const col = t === 'scan' ? TH.hud : t === 'tape' ? TH.accent : TH.accent;
  CX.save(); CX.globalAlpha = p; CX.translate(0, (1 - p) * 40);
  if (t === 'brand' || t === 'playful') { CX.fillStyle = rgba(TH.bg, 0.86); rrect(x0 - 150, y - 66, w + 300, 118, 30); CX.fill(); }
  else { CX.fillStyle = rgba('#000', 0.45); CX.fillRect(x0 - 150, y - 66, w + 300, 118); }
  const lab = MM.labels;
  const ink = t === 'brand' || t === 'playful' ? TH.ink : TH.ink;
  label(MM.name, x0 - 122, y - 34, { color: t === 'scan' ? TH.hud : t === 'tape' ? TH.accent2 : TH.accent,
    size: TH.mono === 'VT323' ? 26 : 16 });
  text(UP(lab[0] || ''), x0 - 22, y + 8, { size: 24, color: ink, align: 'right', alpha: lerp(1, 0.45, u) });
  text(UP(lab[1] || ''), x0 + w + 22, y + 8, { size: 24, color: ink, align: 'left', alpha: lerp(0.45, 1, u) });
  CX.fillStyle = rgba(ink, 0.22); rrect(x0, y - 4, w, 8, 4); CX.fill();
  CX.fillStyle = col; rrect(x0, y - 4, Math.max(8, w * u), 8, 4); CX.fill();
  CX.fillStyle = col; circle(x0 + w * u, y, 14); CX.fill();
  CX.fillStyle = t === 'brand' || t === 'playful' ? '#fff' : TH.bg; circle(x0 + w * u, y, 6); CX.fill();
  if (MM.angle && MM.angle.value) {
    const v = MM.angle.value[k];
    // the readout rides the knob, clear of the name
    const unit = MM.angle.unit || '°';
    const str = unit.trim() === 'mm' ? v.toFixed(1) : String(Math.round(v));
    text(`${str}${unit}`, x0 + w * u, y + 40, { size: 24, color: ink, align: 'center' });
  }
  CX.restore();
}

// ------------------------------------------------------------------------------ lights
SEG.lights = {
  async prepare(f) { return plate('lights', f); },
  draw(f, s, bm) {
    drawPlate(bm);
    const Lt = D.lights, b = B();
    const on = Lt.power_on;
    // bloom: the bright parts of the plate, blurred and added
    const lit = !(Lt.power_off !== null && Lt.power_off !== undefined && f >= Lt.power_off + 3);
    if (bm && f >= on && lit) {
      const q = tw(f, on, on + b);
      const [c, x] = off('bloom');
      x.filter = `brightness(1.3) contrast(2.6) saturate(1.5) blur(${26 * S}px)`;
      x.drawImage(bm, 0, 0, L, L);
      x.filter = 'none';
      CX.save(); CX.globalCompositeOperation = 'screen'; CX.globalAlpha = 0.75 * q;
      CX.setTransform(1, 0, 0, 1, 0, 0); CX.drawImage(c, 0, 0); CX.restore();
      CX.setTransform(S, 0, 0, S, 0, 0);
    }
    // the flash as they switch on (on the flicker's on frames)
    const k = f - on;
    if (k >= 0 && k < 14 && !(k >= 2 && k < 4) && !(k >= 5 && k < 7)) {
      const q = Math.exp(-k / 3.5);
      const [x, y] = Lt.leds.length ? avgTrack(Lt.leds, f - s.start) : [L / 2, L / 2];
      const g = CX.createRadialGradient(x, y, 10, x, y, 700);
      const col = Lt.leds.length ? Lt.leds[0].color : '#FF3A1A';
      g.addColorStop(0, rgba(mix(col, '#ffffff', 0.6), 0.85 * q)); g.addColorStop(0.4, rgba(col, 0.35 * q)); g.addColorStop(1, rgba(col, 0));
      CX.save(); CX.globalCompositeOperation = 'screen'; CX.fillStyle = g; CX.fillRect(0, 0, L, L); CX.restore();
    }
    // reticles lock on to each lamp (and let go when they're switched off)
    const offFade = (Lt.power_off !== null && Lt.power_off !== undefined) ? 1 - tw(f, Lt.power_off, Lt.power_off + 6) : 1;
    Lt.leds.forEach((led, i) => {
      const t0 = on + 6 + i * 4;
      const p = ramp(f, t0, t0 + 12) * offFade;
      if (p <= 0) return;
      const [x, y] = led.track[Math.min(f - s.start, led.track.length - 1)];
      const r = lerp(90, 34, E.outExpo(p));
      const col = TH.name === 'scan' ? TH.hud : '#FFFFFF';
      CX.save(); CX.translate(x, y); CX.rotate((1 - E.outExpo(p)) * 1.2);
      brackets(-r, -r, r, r, 12, rgba(col, clamp(p * 2)), 2.5);
      CX.restore();
      label(led.name || `lamp ${i + 1}`, x + r + 10, y + 5, { color: col, alpha: clamp(p * 2), size: TH.mono === 'VT323' ? 26 : 16 });
    });
    const offf = Lt.power_off;
    const isOff = offf !== null && offf !== undefined && f >= offf;
    const la = tw(f, D.marks.lights.label, D.marks.lights.label + 10, E.outExpo);
    const swap = isOff ? tw(f, offf, offf + 8, E.outExpo) : 1;
    CX.save(); CX.globalAlpha = la * swap; CX.translate(0, (1 - swap) * 24);
    label(isOff ? 'power off' : f < on ? 'lights off' : 'power on', M, TOPY(), { color: TH.name === 'scan' ? TH.hud : TH.accent });
    text(UP(isOff ? Lt.off_label : Lt.label), M, TOPY() + 54,
      { size: 52, color: isOff ? TH.ink : f < on ? rgba('#ffffff', 0.5) : '#FFFFFF',
        shadow: isOff ? rgba('#000', 0.35) : null, blur: 10 });
    CX.restore();
    osd(f, s, '▶ PLAY');
    visor(f, s, 'EMISSION');
  },
};
function avgTrack(leds, k) {
  let x = 0, y = 0;
  leds.forEach(l => { const p = l.track[Math.min(k, l.track.length - 1)]; x += p[0]; y += p[1]; });
  return [x / leds.length, y / leds.length];
}

// ------------------------------------------------------------------------------ lift
SEG.lift = {
  async prepare(f) { return plate('lift', f); },
  draw(f, s, bm) {
    drawPlate(bm);
    const m = D.marks.lift;
    const p = tw(f, m.label, m.label + 12, E.outExpo);
    CX.save(); CX.globalAlpha = p; CX.translate(0, (1 - p) * 30);
    label('lift', M, TOPY(), { color: TH.name === 'scan' ? TH.hud : TH.accent });
    text(UP(D.lift.label), M, TOPY() + 54, { size: 52, color: '#FFFFFF' });
    CX.restore();
    osd(f, s, '▶ PLAY');
    visor(f, s, 'HOVER');
  },
};

// ------------------------------------------------------------------------------ colourways
SEG.colourways = {
  async prepare(f, s) {
    const cw = D.colourways;
    const out = {};
    for (const name of cw.order) {
      const [a, b] = cw.frames[name];
      if (f >= a && f < b) out[name] = await plate('colourways', f, name === cw.order[0] ? null : name);
    }
    return out;
  },
  draw(f, s, P) {
    const cw = D.colourways, m = D.marks.colourways, b = B();
    const names = cw.order;
    // which colourway is showing, and the wipe in progress
    let cur = 0;
    cw.wipes.forEach((w, i) => { if (f >= w[1]) cur = i + 1; });
    const wi = cw.wipes.findIndex(w => f >= w[0] && f < w[1]);
    drawPlate(P[names[cur]]);
    if (wi >= 0) {
      const [w0, w1] = cw.wipes[wi];
      const p = E.inOutCubic(ramp(f, w0, w1));
      wipe(f, p, P[names[wi + 1]], wi);
    }
    // the label: which colourway, its swatches
    const it = cw.items;
    const show = wi >= 0 ? (ramp(f, cw.wipes[wi][0], cw.wipes[wi][1]) > 0.5 ? wi + 1 : wi) : cur;
    const t0 = show === 0 ? m.labels[0] : cw.wipes[show - 1][1] - b / 2;
    const lp = ramp(f, t0, t0 + 12);
    const outp = wi >= 0 && show === wi ? ramp(f, cw.wipes[wi][0], cw.wipes[wi][0] + (cw.wipes[wi][1] - cw.wipes[wi][0]) / 2) : 0;
    colourwayLabel(it[show], show, names.length, lp * (1 - outp), f - t0);
    osd(f, s, `CH ${String(show + 1).padStart(2, '0')}`);
    visor(f, s, `COLOURWAY ${show + 1}/${names.length}`);
  },
};

function wipe(f, p, bm, i) {
  const t = TH.name;
  if (t === 'tape') {                       // a tracking band rolls down the new tape
    const y = lerp(-80, L + 80, p);
    CX.save(); CX.beginPath(); CX.rect(0, 0, L, y); CX.clip(); drawPlate(bm); CX.restore();
    for (let k = 0; k < 18; k++) {
      const yy = y - 40 + k * 5;
      const dx = (hash(f, k) - 0.5) * 70;
      CX.save(); CX.beginPath(); CX.rect(0, yy, L, 5); CX.clip();
      CX.globalAlpha = 0.85; drawPlate(bm, { dx });
      CX.restore();
    }
    CX.save(); CX.globalCompositeOperation = 'screen';
    const g = CX.createLinearGradient(0, y - 50, 0, y + 50);
    g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.35)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    CX.fillStyle = g; CX.fillRect(0, y - 50, L, 100); CX.restore();
    return;
  }
  if (t === 'scan') {                       // a scan line sweeps up
    const y = lerp(L + 40, -40, p);
    CX.save(); CX.beginPath(); CX.rect(0, y, L, L - y); CX.clip(); drawPlate(bm); CX.restore();
    CX.save(); CX.shadowColor = TH.xray; CX.shadowBlur = 24; CX.fillStyle = mix(TH.xray, '#fff', 0.5);
    CX.fillRect(0, y - 1.5, L, 3); CX.restore();
    return;
  }
  // playful and brand: a wobbly edge sweeps across, paw prints (or studs) running along it
  const x = lerp(-160, L + 160, p);
  const edge = y => x + Math.sin(y / 70 + f * 0.35) * 38 + Math.sin(y / 23 - f * 0.2) * 10;
  CX.save(); CX.beginPath(); CX.moveTo(-10, -10);
  for (let y = -10; y <= L + 10; y += 20) CX.lineTo(edge(y), y);
  CX.lineTo(-10, L + 10); CX.closePath(); CX.clip(); drawPlate(bm); CX.restore();
  CX.save(); CX.strokeStyle = TH.bg2; CX.lineWidth = 14; CX.lineJoin = 'round';
  CX.beginPath(); for (let y = -10; y <= L + 10; y += 20) { if (y === -10) CX.moveTo(edge(y), y); else CX.lineTo(edge(y), y); } CX.stroke();
  CX.strokeStyle = TH.accent; CX.lineWidth = 5; CX.stroke(); CX.restore();
  for (let k = 0; k < 7; k++) {
    const y = 90 + k * 150 + (k % 2) * 40;
    const px = edge(y) - 70 - (k % 2) * 60;
    const a = clamp(p * 6) * clamp((1 - p) * 6);
    if (t === 'playful') pawPrint(px, y, 44, TH.ink, Math.PI / 2 + (k % 2 ? 0.25 : -0.25), CX, 0.8 * a);
    else { CX.save(); CX.globalAlpha *= a; brickTop(px, y, 2, 1, 26, TH.accent); CX.restore(); }
  }
}

function colourwayLabel(it, idx, n, p, k) {
  if (!it || p <= 0) return;
  const t = TH.name;
  const x = M, y = L - M - 150;
  CX.save();
  CX.globalAlpha = clamp(p * 2);
  label(`colourway ${idx + 1} / ${n}`, x, y, { color: t === 'scan' ? TH.hud : t === 'tape' ? TH.accent2 : TH.accent, size: TH.mono === 'VT323' ? 32 : 20 });
  const size = fitSize(UP(it.title), 84, L - 2 * M, 700);
  if (t === 'playful') {
    kinetic(UP(it.title), x, y + 84, font(size, 700), (i) => {
      const q = clamp((k - i * 1.5) / 12);
      const w = Math.exp(-q * 5) * Math.cos(q * 12);
      return { alpha: q > 0 ? 1 : 0, sx: 1 + 0.25 * w, sy: 1 - 0.25 * w, dy: -w * 20 };
    }, { spacing: -1 });
  } else {
    CX.save(); CX.beginPath(); CX.rect(0, y + 4, L, 100); CX.clip();
    text(UP(it.title), x, y + 84 + (1 - E.outExpo(p)) * 90, { size, color: t === 'brand' ? TH.ink : '#FFFFFF', spacing: -1,
      shadow: t === 'brand' ? rgba('#ffffff', 0.8) : rgba('#000', 0.6), blur: 14 });
    CX.restore();
  }
  // swatches
  let sx = x + 4;
  it.swatches.forEach((sw, j) => {
    const q = ramp(k, 6 + j * 3, 18 + j * 3);
    if (q <= 0) return;
    const r = 20;                             // a flat 1 x 1 tile of the colour
    CX.save(); CX.translate(sx + r, y + 126); CX.scale(E.outBack(q), E.outBack(q));
    CX.fillStyle = sw.rgb; rrect(-r, -r, 2 * r, 2 * r, 6); CX.fill();
    CX.strokeStyle = rgba(t === 'brand' || t === 'playful' ? TH.ink : '#ffffff', 0.4); CX.lineWidth = 1.5;
    rrect(-r, -r, 2 * r, 2 * r, 6); CX.stroke();
    CX.restore();
    const nm = sw.name;
    const fnt = monoFont(TH.mono === 'VT323' ? 28 : 19);
    text(TH.mono === 'Fredoka' ? nm : UP(nm), sx + 2 * r + 10, y + 132, { font: fnt, color: t === 'brand' || t === 'playful' ? TH.ink : '#FFFFFF', alpha: clamp(q * 2),
      shadow: t === 'brand' || t === 'playful' ? rgba('#fff', 0.8) : rgba('#000', 0.7), blur: 8, spacing: 1 });
    sx += 2 * r + 24 + measure(TH.mono === 'Fredoka' ? nm : UP(nm), fnt, 1);
  });
  CX.restore();
}

// ------------------------------------------------------------------------------ booklet
SEG.booklet = {
  async prepare(f) { return plate('booklet', f); },
  draw(f, s, bm) {
    drawPlate(bm, { raw: true });
    const m = D.marks.booklet, b = B();
    const p = tw(f, m.head, m.head + 12, E.outExpo);
    CX.save(); CX.globalAlpha = p; CX.translate(0, (1 - p) * 30);
    label('build it yourself', M, 104, { color: TH.brand.black });
    text(`${fmt(D.model.steps)} STEPS`, M - 3, 176, { size: 76, color: TH.brand.black, spacing: -1 });
    if (D.booklet) text(`${D.booklet.pages} PAGES`, M, 232, { size: 40, color: TH.brand.black, alpha: 0.7 });
    CX.restore();
    const files = (D.booklet && D.booklet.files) || [];
    let x = M;
    files.forEach((fl, k) => {
      const t0 = m.chips[k] || m.chips[m.chips.length - 1];
      const q = ramp(f, t0, t0 + 9);
      const save = TH; TH = Object.assign({}, TH, { name: 'brand', mono: 'Space Mono', ink: TH.brand.black, bg2: TH.brand.yellow, bg: TH.brand.cream, hud_ink: TH.brand.cream });
      const w = chip('', fl, x, L - M - 62, q, k, { h: 56 });
      TH = save;
      x += w + 12;
    });
  },
};

// ------------------------------------------------------------------------------ outro
SEG.outro = {
  shake(f) { shakeAt(f, [D.marks.outro.logo + 6], 6, 8); },
  draw(f, s) {
    const m = D.marks.outro, b = B();
    const Y = TH.brand.yellow, K = TH.brand.black;
    CX.fillStyle = Y; CX.fillRect(0, 0, L, L);
    for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 20, mix(Y, '#ffffff', 0.08), CX, 0.55);
    const logo = IMG.get(D.logo);
    const lp = ramp(f, m.logo, m.logo + 16);
    if (logo && lp > 0) {
      const w = 560, h = logo.height * w / logo.width;
      const sc = E.spring(lp, 1.4, 5.5);
      const drop = (1 - E.outCubic(clamp(lp * 2.2))) * -500;
      CX.save(); CX.translate(L / 2, 430 + drop); CX.scale(sc, sc); CX.rotate((1 - sc) * 0.2);
      CX.drawImage(logo, -w / 2, -h / 2, w, h);
      CX.restore();
    }
    // the URL types on
    const url = D.model.url;
    const n = Math.floor(clamp((f - m.url) / 0.7, 0, url.length));
    if (f >= m.url) {
      const fnt = font(44, 600, 'Space Mono');
      const full = measure(url, fnt);
      const x = L / 2 - full / 2, y = 780;
      CX.save();
      CX.fillStyle = K; rrect(x - 30, y - 50, full + 60, 72, 36); CX.fill();
      text(url.slice(0, n), x, y, { font: fnt, color: Y });
      if (n < url.length || (f % 16) < 8) {
        const cw = measure(url.slice(0, n), fnt);
        CX.fillStyle = Y; CX.fillRect(x + cw + 4, y - 34, 4, 42);
      }
      CX.restore();
    }
    const fp = tw(f, m.fine, m.fine + 12);
    text(D.model.disclaimer, L / 2, 930, { font: font(24, 500), color: K, align: 'center', alpha: fp * 0.85 });
    if (D.model.notice) text(D.model.notice, L / 2, 966, { font: font(19, 400), color: K, align: 'center', alpha: fp * 0.6 });
  },
};

SEG.blank = { draw(f) { background(f); } };
