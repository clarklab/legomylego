/* brickkit sizzle reel: several models in one quick reel (plan: brickkit/video/sizzle.py).
 *
 * Loaded after core.js, segments.js and fx.js (sizzle.html), it adds four drawers:
 *   sz_open    the logo lands, the tagline slams word by word on coloured cards, then one beat
 *              per model: its cut-out on a card of its own
 *   sz_model   one model: its footage (build time-lapse, signature moment, turntable, ...)
 *              punched on the beats, its name slammed onto yellow labels, an index tag, stat
 *              chips, a caption typed on
 *   sz_finale  the models' turntables in a 2 x 2 grid popping in on the beats; the line
 *   sz_outro   the logo, the URL typed onto a yellow pill, the small print
 * The site's look throughout: Inter set tight, Menlo caps for small labels, brand yellow, ink,
 * cream and brick red.
 */
'use strict';

const SZ = () => ({ Y: TH.brand.yellow, K: TH.brand.black, P: TH.brand.cream, R: TH.brand.red });
const szUrl = (slug, src, k) => `work/footage/${slug}/${src}/${pad(k)}.jpg`;
function szShot(s, f) {
  return s.shots.find(sh => f >= sh.start && f < sh.end) || s.shots[s.shots.length - 1];
}
const szFrame = (sh, f) => Math.max(0, Math.min(sh.n - 1, Math.round(sh.from + (f - sh.start) * sh.speed)));
async function szImg(url) { USED.add(url); return img(url); }
// the beat's punch: a quick zoom that eases back
function punch(f, beats, amt = 0.028, len = 6) {
  let p = 0;
  for (const b of beats || []) { const t = f - b; if (t >= 0 && t < len) p = Math.max(p, Math.pow(1 - t / len, 2)); }
  return 1 + amt * p;
}
function coverImg(bm, sc = 1, dx = 0, dy = 0) {
  if (!bm) { CX.fillStyle = '#2A2824'; CX.fillRect(0, 0, L, L); return; }
  CX.save();
  CX.translate(L / 2 + dx, L / 2 + dy); CX.scale(sc, sc); CX.translate(-L / 2, -L / 2);
  CX.drawImage(bm, 0, 0, L, L);
  CX.restore();
}
// words that fit a width, at most `size`, broken into lines at spaces (balanced)
function szLines(str, size, maxW, weight = 800) {
  const up = UP(str);
  const w1 = measure(up, font(size, weight), -size * 0.028);
  if (w1 <= maxW || !up.includes(' ')) return { lines: [up], size: Math.min(size, fitSize(up, size, maxW, weight, null, -0.028)) };
  const words = up.split(' ');
  let best = null;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(' '), b = words.slice(i).join(' ');
    const w = Math.max(measure(a, font(size, weight), -size * 0.028), measure(b, font(size, weight), -size * 0.028));
    if (!best || w < best[0]) best = [w, [a, b]];
  }
  return { lines: best[1], size: Math.min(size, Math.floor(size * maxW / best[0])) };
}
// a word slams in: big to size with a little overshoot and motion smear
function slamWord(w, x, y, size, col, k, align = 'left', weight = 800) {
  if (k < 0) return;
  const q = clamp(k / 7);
  const sc = 1.55 - 0.55 * E.outBack(q, 2.4);
  const fnt = font(size, weight), sp = -size * 0.028;
  const ww = measure(w, fnt, sp);
  const cx = align === 'center' ? x : x + ww / 2, cy = y - size * 0.36;
  for (let g = 2; g >= 0; g--) {
    const a = g > 0 ? clamp(1 - q * 3) * 0.2 : clamp(q * 4);
    if (a <= 0.005) continue;
    CX.save(); CX.translate(cx, cy); CX.scale(sc * (1 + g * 0.16), sc * (1 + g * 0.16));
    text(w, -ww / 2, size * 0.36, { font: fnt, color: col, alpha: a, spacing: sp });
    CX.restore();
  }
}
function checkBadge(x, y, r, p, col, ink) {
  if (p <= 0) return;
  const sc = E.outBack(clamp(p * 1.4), 2.2);
  CX.save(); CX.translate(x, y); CX.scale(sc, sc);
  CX.fillStyle = col; circle(0, 0, r); CX.fill();
  checkMark(0, 0, r * 1.25, ink, clamp(p * 2 - 0.4), r * 0.24);
  CX.restore();
}
// a small yellow tag: Menlo caps on a pill
function tag(str, x, y, o = {}) {
  const c = SZ();
  const size = o.size || 17;
  const w = labelWidth(str, size) + 28, h = size + 18;
  CX.save(); CX.globalAlpha *= o.alpha === undefined ? 1 : o.alpha;
  CX.fillStyle = o.bg || c.Y; rrect(x, y - h / 2, w, h, h / 2); CX.fill();
  label(str, x + 14, y + size * 0.36, { size, color: o.color || c.K });
  CX.restore();
  return w;
}

// ------------------------------------------------------------------------------ open
SEG.sz_open = {
  async prepare(f, s) {
    const t = s.teaser.find(t => f >= t.start && f < t.end);
    return t ? szImg(`work/footage/${t.slug}/hero.png`) : null;
  },
  shake(f, s) {
    shakeAt(f, [s.logo], 12, 9);
    shakeAt(f, s.words.map(w => w[1]), 7, 6);
  },
  draw(f, s, hero) {
    const c = SZ();
    const cards = s.cards;
    const teaser = s.teaser.find(t => f >= t.start && f < t.end);
    if (teaser) {                                   // one beat per model: its cut-out on a card
      const k = s.teaser.indexOf(teaser);
      const bg = [c.Y, c.K, c.R, c.P][k % 4], ink = [c.K, c.Y, c.P, c.K][k % 4];
      CX.fillStyle = bg; CX.fillRect(0, 0, L, L);
      for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 20, mix(bg, '#ffffff', 0.08), CX, 0.5);
      const q = E.spring(clamp((f - teaser.start) / 10), 1.8, 6);
      if (hero) {
        const r = Math.min(900 / hero.width, 760 / hero.height);
        const w = hero.width * r, h = hero.height * r;
        CX.save(); CX.translate(L / 2, 500); CX.scale(0.8 + 0.2 * q, 0.8 + 0.2 * q); CX.rotate((1 - q) * (k % 2 ? 0.08 : -0.08));
        CX.drawImage(hero, -w / 2, -h / 2, w, h);
        CX.restore();
      }
      label(`${String(k + 1).padStart(2, '0')} / ${String(s.teaser.length).padStart(2, '0')}`, M, M + 20, { color: ink, size: 18 });
      const nm = UP(teaser.name);
      text(nm, M, L - M - 8, { size: Math.min(64, fitSize(nm, 64, L - 2 * M, 800, null, -0.022)), weight: 800, color: ink,
        alpha: clamp((f - teaser.start) / 4) });
      return;
    }
    if (f < cards[1]) {                             // the logo lands on cream paper
      const w0 = clamp((f + 8) / Math.max(8, s.logo + 8));
      CX.fillStyle = c.P; CX.fillRect(0, 0, L, L);
      for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) {
        const d = Math.hypot(x - L / 2, y - L / 2) / (L * 0.72);
        const q = clamp((w0 * 1.4 - d) / 0.4);
        if (q > 0) stud(x, y, 20 * E.outBack(q, 1.6), mix(c.P, c.K, 0.06), CX, 0.4);
      }
      const logo = IMG.get(D.logo);
      const lp = ramp(f, s.logo - 6, s.logo + 12);
      if (logo && lp > 0) {
        const w = 620, h = logo.height * w / logo.width;
        const sc = E.spring(lp, 1.4, 5.5);
        const drop = (1 - E.outCubic(clamp(lp * 2.4))) * -420;
        CX.save(); CX.translate(L / 2, L / 2 - 10 + drop); CX.scale(sc, sc); CX.rotate((1 - sc) * 0.25);
        CX.drawImage(logo, -w / 2, -h / 2, w, h);
        CX.restore();
      }
      return;
    }
    // the tagline: a card per bar, its words slammed on their beats
    let bar = 1;
    while (bar + 1 < cards.length && f >= cards[bar + 1]) bar++;
    const dark = bar % 2 === 0;
    const bg = dark ? c.K : c.Y, ink = dark ? c.Y : c.K;
    CX.fillStyle = bg; CX.fillRect(0, 0, L, L);
    for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 20, mix(bg, dark ? '#ffffff' : '#000000', 0.06), CX, 0.6);
    const a = cards[bar], b = bar + 1 < cards.length ? cards[bar + 1] : s.end;
    const words = s.words.filter(w => w[1] >= a && w[1] < b);
    const n = words.length;
    const last = words[n - 1];
    const badge = last && /COMPUTER/i.test(last[0]);   // checked: a badge ticks on after it
    const room = L - 2 * M - (badge ? 130 : 0);
    const size = Math.min(190, ...words.map(w => fitSize(UP(w[0]), 190, room, 800, null, -0.028)));
    const lh = size * 0.98;
    const y0 = L / 2 - (n - 1) * lh / 2 + size * 0.36;
    const cx = L / 2 - (badge ? 55 : 0);
    words.forEach(([w, t0], i) => slamWord(UP(w), cx, y0 + i * lh, size, ink, f - t0, 'center'));
    if (badge) {
      const ww = measure(UP(last[0]), font(size, 800), -size * 0.028);
      checkBadge(cx + ww / 2 + 62, y0 + (n - 1) * lh - size * 0.34, 44, ramp(f, last[1] + 3, last[1] + 13), c.R, c.P);
    }
  },
};

// ------------------------------------------------------------------------------ a model
SEG.sz_model = {
  async prepare(f, s) {
    const sh = szShot(s, f);
    return szImg(szUrl(s.slug, sh.src, szFrame(sh, f)));
  },
  draw(f, s, bm) {
    const c = SZ();
    const sh = szShot(s, f);
    const k = s.shots.indexOf(sh);
    const prog = ramp(f, sh.start, sh.end);
    coverImg(bm, (1 + 0.04 * prog) * punch(f, s.beats));
    // legibility: a soft darkening at the bottom and the top-left
    const g = CX.createLinearGradient(0, L * 0.55, 0, L);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.5)');
    CX.fillStyle = g; CX.fillRect(0, L * 0.55, L, L * 0.45);
    const g2 = CX.createLinearGradient(0, 0, 0, 180);
    g2.addColorStop(0, 'rgba(0,0,0,0.3)'); g2.addColorStop(1, 'rgba(0,0,0,0)');
    CX.fillStyle = g2; CX.fillRect(0, 0, L, 180);
    // the index tag, top left (the name joins it once the big name has gone)
    const idx = `${String(s.index).padStart(2, '0')} / ${String(s.count).padStart(2, '0')}`;
    const nameGone = k > 0;
    const ta = tw(f, s.start + 2, s.start + 8, E.outExpo);
    tag(nameGone ? `${idx}  ${s.title}` : idx, M, M + 14, { alpha: ta });
    // the name, slammed onto yellow labels over the first shot
    const first = s.shots[0];
    if (f < first.end + 6) {
      const out = tw(f, first.end - 2, first.end + 5, E.inCubic);
      const fit = szLines(s.title, 132, L - 2 * M - 40);
      const size = fit.size, lh = size * 1.12;
      const n = fit.lines.length;
      const yb = L - M - 30 - (n - 1) * lh;
      fit.lines.forEach((ln, i) => {
        const t0 = s.beats[Math.min(i, s.beats.length - 1)] + i * 2;
        const q = clamp((f - t0) / 7);
        if (q <= 0) return;
        const fnt = font(size, 800), sp = -size * 0.028;
        const w = measure(ln, fnt, sp) + 36;
        const y = yb + i * lh;
        const x0 = M - 18 - out * (w + 200);
        CX.save();
        CX.fillStyle = c.Y; CX.fillRect(x0, y - size * 0.86, w * E.outExpo(q), size * 1.06);
        CX.beginPath(); CX.rect(x0, y - size * 0.86, w, size * 1.06); CX.clip();
        const rise = (1 - E.outBack(clamp((f - t0 - 2) / 7), 1.6)) * size;
        text(ln, x0 + 18, y + rise, { font: fnt, spacing: sp, color: c.K });
        CX.restore();
      });
    }
    // a caption for the shot, typed on (Menlo caps, a brick-red square)
    const cap = sh.caption || (k === 1 ? s.caption : '');
    if (cap && k > 0) {
      const n = Math.floor(clamp((f - sh.start - 2) / 8) * cap.length + 1e-6);
      const y = L - M - 4 - (s.chips.some(ch => f >= ch.at) ? 84 : 0);
      CX.fillStyle = c.R; CX.fillRect(M, y - 17, 14, 14);
      label(UP(cap).slice(0, n), M + 26, y - 4, { color: c.P, size: 19, shadow: 'rgba(0,0,0,0.6)', blur: 8 });
    }
    // stat chips, popping in on their beats
    let x = M;
    s.chips.forEach((ch, i) => {
      if (f < ch.at) return;
      const w = chip(UP(ch.value), ch.label, x, L - M - 62, ramp(f, ch.at, ch.at + 8), i, { vsize: 30 });
      x += w + 14;
    });
  },
};

// ------------------------------------------------------------------------------ finale
SEG.sz_finale = {
  async prepare(f, s) {
    const out = [];
    for (const cell of s.cells) {
      const k = Math.floor(cell.from * 360 + (f - s.start) * 1.4) % 360;
      out.push(f >= cell.at - 1 ? await szImg(szUrl(cell.slug, 'turntable', k)) : null);
    }
    return out;
  },
  draw(f, s, bms) {
    const c = SZ();
    CX.fillStyle = c.P; CX.fillRect(0, 0, L, L);
    const gap = 14, cs = (L - 3 * gap) / 2;
    const pz = punch(f, s.beats, 0.012);
    const la = s.line_at;
    const room = E.inOutCubic(ramp(f, la[0] - 8, la[0] + 6));    // the grid moves up for the line
    const gs = lerp(1, 0.72, room);
    CX.save(); CX.translate(L / 2, 0); CX.scale(gs * pz, gs * pz); CX.translate(-L / 2, 0);
    s.cells.forEach((cell, i) => {
      const x = gap + (i % 2) * (cs + gap), y = gap + Math.floor(i / 2) * (cs + gap);
      const q = E.spring(clamp((f - cell.at) / 12), 1.6, 6);
      if (f < cell.at) {
        CX.fillStyle = mix(c.P, c.K, 0.06); rrect(x, y, cs, cs, 18); CX.fill();
        return;
      }
      CX.save();
      CX.translate(x + cs / 2, y + cs / 2); CX.scale(0.7 + 0.3 * q, 0.7 + 0.3 * q); CX.translate(-cs / 2, -cs / 2);
      CX.beginPath(); CX.roundRect(0, 0, cs, cs, 18); CX.clip();
      if (bms[i]) CX.drawImage(bms[i], 0, 0, cs, cs);
      CX.restore();
      tag(UP(cell.name), x + 22, y + cs - 38, { alpha: clamp((f - cell.at - 4) / 6), size: 23 });
    });
    CX.restore();
    // the line, on an ink band under the grid
    if (f >= la[0]) {
      const p = E.outExpo(ramp(f, la[0], la[0] + 10));
      const by = L * 0.72 + 10;
      const bh = L - by;
      CX.fillStyle = c.K; CX.fillRect(0, by, L * p, bh);
      s.line.forEach((ln, i) => {
        if (f < la[i]) return;
        let str = UP(ln);
        const q = ramp(f, la[i], la[i] + 12);
        // the piece count counts up
        const num = fmt(s.pieces);
        if (str.includes(num)) str = str.replace(num, fmt(Math.round(s.pieces * E.outCubic(q))));
        const size = Math.min(72, fitSize(UP(ln), 72, L - 2 * M - (i === s.line.length - 1 ? 90 : 0), 800, null, -0.022));
        const y = by + 30 + (i + 0.8) * 100;
        CX.save(); CX.beginPath(); CX.rect(0, by, L * p, bh); CX.clip();
        const dx = (1 - E.outExpo(clamp(q * 1.5))) * 80;
        text(str, M + dx, y, { size, weight: 800, color: i === s.line.length - 1 ? c.Y : c.P, alpha: clamp(q * 3) });
        CX.restore();
        if (i === s.line.length - 1) {
          const w = measure(UP(ln), font(size, 800), track(size));
          checkBadge(M + w + 50, y - size * 0.34, 30, ramp(f, la[i] + 4, la[i] + 14), c.R, c.P);
        }
      });
    }
  },
};

// ------------------------------------------------------------------------------ outro
SEG.sz_outro = {
  shake(f, s) { shakeAt(f, [s.logo + 6], 6, 8); },
  draw(f, s) {
    const c = SZ();
    CX.fillStyle = c.P; CX.fillRect(0, 0, L, L);
    for (let x = 30; x < L; x += 60) for (let y = 30; y < L; y += 60) stud(x, y, 20, mix(c.P, c.K, 0.05), CX, 0.35);
    const logo = IMG.get(D.logo);
    const lp = ramp(f, s.logo, s.logo + 16);
    if (logo && lp > 0) {
      const w = 600, h = logo.height * w / logo.width;
      const sc = E.spring(lp, 1.4, 5.5);
      const drop = (1 - E.outCubic(clamp(lp * 2.2))) * -500;
      CX.save(); CX.translate(L / 2, 420 + drop); CX.scale(sc, sc); CX.rotate((1 - sc) * 0.2);
      CX.drawImage(logo, -w / 2, -h / 2, w, h);
      CX.restore();
    }
    const url = s.url;
    if (url && f >= s.url_at) {
      const n = Math.floor(clamp((f - s.url_at) / 0.7, 0, url.length));
      const fnt = font(fitSize(url, 46, L - 2 * M - 80, 600, TH.brand_mono), 600, TH.brand_mono);
      const full = measure(url, fnt);
      const x = L / 2 - full / 2, y = 790;
      CX.fillStyle = c.Y; rrect(x - 32, y - 52, full + 64, 76, 38); CX.fill();
      text(url.slice(0, n), x, y, { font: fnt, color: c.K });
      if (n < url.length || (f % 16) < 8) { const cw = measure(url.slice(0, n), fnt); CX.fillStyle = c.K; CX.fillRect(x + cw + 4, y - 36, 4, 44); }
    }
    const fp = tw(f, s.fine_at, s.fine_at + 12);
    const fine = (str, sz, wt) => font(Math.min(sz, fitSize(str, sz, L - 2 * M, wt)), wt);
    if (s.disclaimer) text(s.disclaimer, L / 2, 928, { font: fine(s.disclaimer, 23, 500), color: c.K, align: 'center', alpha: fp * 0.85 });
    s.notices.forEach((nt, i) => text(nt, L / 2, 962 + i * 26, { font: fine(nt, 17, 400), color: c.K, align: 'center', alpha: fp * 0.6 }));
  },
};
