// Shared helpers for every page: theme toggle, data fetching, formatting, asset URLs, footer notices.
import { hydrateIcons } from './icons.js';

export const SITE = {
  name: "L'Eggo my LEGO",
  url: 'https://lego.superfun.games',
};

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export const fmtInt = (n) => Number(n || 0).toLocaleString('en-US');

export function fmtCm(mm) {
  const cm = mm / 10;
  return cm >= 100 ? cm.toFixed(0) : cm.toFixed(1).replace(/\.0$/, '');
}

export function fmtBytes(n) {
  if (!n && n !== 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export const plural = (n, one, many = one + 's') => `${fmtInt(n)} ${n === 1 ? one : many}`;

export function humanize(name) {
  return String(name || '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().replace(/^./, (c) => c.toUpperCase());
}

export async function getJSON(url, { optional = false } = {}) {
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return await r.json();
  } catch (e) {
    if (optional) return null;
    throw e;
  }
}

// Cheap stable hash (FNV-1a) used as a cache-busting fallback when media.json lacks an entry.
export function hash(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

const encPath = (p) => String(p).split('/').map(encodeURIComponent).join('/');

// media.json is written by tools/site_assets.py: content hashes, sizes and web-sized image copies.
export class Media {
  constructor(media, slug, fallbackVersion = '') {
    this.m = media?.models?.[slug] || {};
    this.slug = slug;
    this.fallback = fallbackVersion;
  }
  url(path) {
    const f = this.m.files?.[path];
    // Include the model.json hash too, so a re-export without re-running site_assets.py still
    // gets fresh URLs (files are cached for a year).
    const v = [f?.v, this.fallback].filter(Boolean).join('-');
    return `/models/${encodeURIComponent(this.slug)}/${encPath(path)}${v ? `?v=${v}` : ''}`;
  }
  size(path) {
    return this.m.files?.[path]?.size;
  }
  // size: 'sm' (about 480px) or 'lg' (full size); falls back to the original PNG.
  image(path, size = 'lg') {
    const img = this.m.images?.[path];
    if (img?.[size]) return img[size];
    return this.url(path);
  }
  imageInfo(path) {
    return this.m.images?.[path] || null;
  }
}

export const CHECK_INFO = {
  real_elements: ['Real elements', 'Every part exists as a real LEGO element in that colour', 'tag'],
  connections: ['Connections', 'Every stud, pin and axle joint is found and counted', 'link'],
  collisions: ['No collisions', 'No two parts try to occupy the same space', 'collision'],
  buildability: ['Buildable steps', 'Each part slides into place, in order, without hitting anything', 'steps'],
  stability: ['Stability', 'Centre of mass over the footprint, and tipping angle', 'scale'],
  mechanism: ['Mechanism', 'Moving parts swept through their full range: no clashes, gears mesh', 'gear'],
  electrics: ['Electrics', 'Lights and cables: every cable run is long enough', 'bolt'],
  technique: ['Technique', 'Brittle clips, moving transparent parts and other risky techniques', 'wand'],
};

export function checkInfo(name) {
  return CHECK_INFO[name] || [humanize(name), '', 'shield'];
}

export function checkCounts(checks = []) {
  const c = { pass: 0, warn: 0, fail: 0 };
  for (const k of checks) if (k.status in c) c[k.status]++;
  return c;
}

export function statusBadge(status, label) {
  const map = {
    pass: ['badge-pass', 'checkCircle', 'Checks pass'],
    warn: ['badge-warn', 'alert', 'Passed with notes'],
    fail: ['badge-fail', 'xCircle', 'Check failed'],
    unknown: ['badge-unknown', 'info', 'Not checked yet'],
  };
  const [cls, ic, text] = map[status] || map.unknown;
  return { cls, icon: ic, text: label || text };
}

// Model-specific trademark notices: from the model data (`notice`, if the export adds it) or site.json.
export function noticeFor(slug, model, siteConf) {
  return model?.notice || model?.credits || siteConf?.notices?.[slug] || '';
}

export function renderNotices(list) {
  const el = document.getElementById('model-notices');
  if (!el) return;
  const uniq = [...new Set(list.filter(Boolean))];
  el.textContent = uniq.join(' ');
  el.hidden = !uniq.length;
}

function initTheme() {
  const btn = document.querySelector('.theme-toggle');
  if (!btn) return;
  const media = matchMedia('(prefers-color-scheme: dark)');
  const effective = () => document.documentElement.dataset.theme || (media.matches ? 'dark' : 'light');
  const sync = () => {
    const dark = effective() === 'dark';
    btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    btn.title = btn.getAttribute('aria-label');
  };
  btn.addEventListener('click', () => {
    const next = effective() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) { /* private mode */ }
    sync();
    document.dispatchEvent(new CustomEvent('themechange'));
  });
  media.addEventListener?.('change', () => {
    sync();
    document.dispatchEvent(new CustomEvent('themechange'));
  });
  sync();
}

export function initSite() {
  hydrateIcons();
  initTheme();
  const y = document.getElementById('year');
  if (y) y.textContent = String(new Date().getFullYear());
}
