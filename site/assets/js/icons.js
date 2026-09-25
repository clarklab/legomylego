// Small inline SVG icon set (24x24, 2px round strokes, currentColor).
const P = {
  play: '<path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.3-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6" y="4.5" width="4" height="15" rx="1.2" fill="currentColor" stroke="none"/><rect x="14" y="4.5" width="4" height="15" rx="1.2" fill="currentColor" stroke="none"/>',
  prev: '<path d="M15 18 9 12l6-6"/>',
  next: '<path d="m9 18 6-6-6-6"/>',
  orbit: '<path d="M21 12a9 9 0 1 1-3.1-6.8"/><path d="M21 4v5h-5"/><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/>',
  reset: '<path d="M3 12a9 9 0 1 0 2.64-6.36L3 8.3"/><path d="M3 3.5v4.8h4.8"/>',
  expand: '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/><path d="M8 21H5a2 2 0 0 1-2-2v-3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
  shrink: '<path d="M8 3v3a2 2 0 0 1-2 2H3"/><path d="M16 3v3a2 2 0 0 0 2 2h3"/><path d="M8 21v-3a2 2 0 0 0-2-2H3"/><path d="M16 21v-3a2 2 0 0 1 2-2h3"/>',
  bulb: '<path d="M9 18h6"/><path d="M10 21.5h4"/><path d="M12 2.5a6.5 6.5 0 0 0-4 11.63c.64.5 1 1.24 1 2.04V16h6v-.13c0-.8.37-1.55 1-2.04A6.5 6.5 0 0 0 12 2.5z"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 8.9 19.4a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c.14.6.66 1 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1z"/>',
  brick: '<rect x="2.5" y="9" width="19" height="11" rx="2"/><path d="M6 9V6.5A1.5 1.5 0 0 1 7.5 5h1A1.5 1.5 0 0 1 10 6.5V9"/><path d="M14 9V6.5A1.5 1.5 0 0 1 15.5 5h1A1.5 1.5 0 0 1 18 6.5V9"/>',
  ruler: '<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.4 2.4 0 0 1 0-3.4l2.6-2.6a2.4 2.4 0 0 1 3.4 0z"/><path d="m14.5 12.5 2-2"/><path d="m11.5 9.5 2-2"/><path d="m8.5 6.5 2-2"/><path d="m17.5 15.5 2-2"/>',
  steps: '<path d="M4 20h4v-4h4v-4h4V8h4"/><path d="M4 20V4"/>',
  palette: '<circle cx="13.5" cy="6.5" r="1.2" fill="currentColor"/><circle cx="17.5" cy="10.5" r="1.2" fill="currentColor"/><circle cx="8.5" cy="7.5" r="1.2" fill="currentColor"/><circle cx="6.5" cy="12.5" r="1.2" fill="currentColor"/><path d="M12 2a10 10 0 0 0 0 20c.9 0 1.6-.7 1.6-1.6 0-.42-.16-.8-.42-1.08a1.6 1.6 0 0 1 1.2-2.7H16a6 6 0 0 0 6-6C22 6 17.5 2 12 2z"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkCircle: '<circle cx="12" cy="12" r="9.5"/><path d="m8 12.3 2.7 2.7L16 9.6"/>',
  shield: '<path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  alert: '<path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  xCircle: '<circle cx="12" cy="12" r="9.5"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
  info: '<circle cx="12" cy="12" r="9.5"/><path d="M12 16v-4.5"/><path d="M12 8h.01"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
  book: '<path d="M4 19.5V5a2.5 2.5 0 0 1 2.5-2.5H20v17H6.5A2.5 2.5 0 0 0 4 22"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M9 7h7"/><path d="M9 11h5"/>',
  film: '<rect x="2.5" y="4" width="19" height="16" rx="2.5"/><path d="m10 9 5 3-5 3z" fill="currentColor"/>',
  cube: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/>',
  list: '<path d="M9 6h11"/><path d="M9 12h11"/><path d="M9 18h11"/><circle cx="4.5" cy="6" r="1" fill="currentColor"/><circle cx="4.5" cy="12" r="1" fill="currentColor"/><circle cx="4.5" cy="18" r="1" fill="currentColor"/>',
  cart: '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2.5 3h2.6l2.4 11.6a2 2 0 0 0 2 1.6h8.2a2 2 0 0 0 2-1.5L21.5 8H6"/>',
  tag: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5" fill="currentColor"/>',
  external: '<path d="M14 4h6v6"/><path d="M10 14 20 4"/><path d="M19 14v5a1.5 1.5 0 0 1-1.5 1.5h-12A1.5 1.5 0 0 1 4 19V6.5A1.5 1.5 0 0 1 5.5 5H10"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m4.9 19.1 1.4-1.4"/><path d="m17.7 6.3 1.4-1.4"/>',
  moon: '<path d="M20.5 14.5A8.5 8.5 0 1 1 9.5 3.5a7 7 0 0 0 11 11z"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  hand: '<path d="M18 11V6a2 2 0 0 0-4 0v5"/><path d="M14 10V4a2 2 0 0 0-4 0v6"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>',
  collision: '<rect x="3" y="8" width="10" height="10" rx="2"/><rect x="11" y="4" width="10" height="10" rx="2"/><path d="M11 8h2v6h-2" fill="currentColor" stroke="none" opacity=".35"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  scale: '<path d="M12 3v18"/><path d="M5 21h14"/><path d="M3 7h18"/><path d="m6 7-3 7a3.5 3.5 0 0 0 6 0z"/><path d="m18 7-3 7a3.5 3.5 0 0 0 6 0z"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  wand: '<path d="m15 4 5 5"/><path d="M3 21 16.5 7.5"/><path d="M8 2v3"/><path d="M6.5 3.5h3"/><path d="M20 13v3"/><path d="M18.5 14.5h3"/>',
  code: '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
};

export function icon(name, cls = '') {
  const body = P[name] || P.info;
  return `<svg class="icon${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
}

// Replace <i data-icon="name"></i> placeholders in static markup.
export function hydrateIcons(root = document) {
  root.querySelectorAll('i[data-icon]').forEach((el) => {
    const tpl = document.createElement('template');
    tpl.innerHTML = icon(el.dataset.icon, el.className);
    el.replaceWith(tpl.content.firstChild);
  });
}
